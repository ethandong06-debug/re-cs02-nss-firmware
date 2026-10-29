/*
 * athena_stats.c - AthenaWrt resident resource-stats plugin for rpcd
 *
 * Sits inside the running rpcd process (dlopen'd from /usr/lib/rpcd/*.so),
 * so every sample is pure read()/getdents() on /proc. No fork, no exec.
 *
 * ubus object : athena-stats
 * ubus method : stats        ->  { cpu:{...}, memory:{...}, procs:[...] }
 *
 * State (previous cpu ticks / per-pid ticks) is kept in process memory,
 * exactly the way the vendor daemons in GWRT do it.
 *
 * License: GPL-2.0
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#include <time.h>
#include <limits.h>
#include <sys/types.h>
#include <sys/stat.h>

#include <libubus.h>
#include <libubox/blobmsg.h>
#include <libubox/blobmsg_json.h>
#include <rpcd/plugin.h>

#define MAX_PROCS     512
#define MAX_OUTPUT    60
#define NAME_LEN      32

struct pent {
	int  pid;
	unsigned long long ticks;      /* utime + stime, in USER_HZ */
	unsigned long long rss_kb;
	char name[NAME_LEN];
};

/* ---- process-local state (survives across ubus calls) ---- */
static struct pent  s_prev[MAX_PROCS];
static int          s_prev_n;
static unsigned long long s_prev_total, s_prev_idle;
static struct timespec    s_prev_ts;
static int          s_have_prev;

/* read the first line of /proc/stat: cpu user nice system idle iowait irq softirq steal */
static int read_cpu_totals(unsigned long long *total, unsigned long long *idle)
{
	FILE *fp = fopen("/proc/stat", "r");
	unsigned long long v[10];
	int n, i;
	unsigned long long sum = 0;

	if (!fp)
		return -1;

	n = fscanf(fp, "cpu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
		   &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9]);
	fclose(fp);

	if (n < 4)
		return -1;

	/* total = everything except guest/guest_nice (indices 8,9 are guest, they are
	 * already accounted inside user/nice) -> sum only the first 8 fields present */
	for (i = 0; i < n && i < 8; i++)
		sum += v[i];

	*total = sum;
	*idle  = v[3] + (n > 4 ? v[4] : 0);   /* idle + iowait */
	return 0;
}

/* /proc/meminfo -> MemTotal / MemAvailable in kB, plus RSS of processes is
 * accumulated separately while scanning /proc */
static int read_meminfo(unsigned long long *total_kb, unsigned long long *avail_kb)
{
	FILE *fp = fopen("/proc/meminfo", "r");
	char line[256];
	int got_t = 0, got_a = 0;

	if (!fp)
		return -1;

	while (fgets(line, sizeof(line), fp)) {
		if (!strncmp(line, "MemTotal:", 9)) {
			*total_kb = strtoull(line + 9, NULL, 10);
			got_t = 1;
		} else if (!strncmp(line, "MemAvailable:", 13)) {
			*avail_kb = strtoull(line + 13, NULL, 10);
			got_a = 1;
		}
		if (got_t && got_a)
			break;
	}
	fclose(fp);
	return (got_t && got_a) ? 0 : -1;
}

/* highest thermal zone temperature in degrees C, 0 if none */
static int read_temp(void)
{
	DIR *d = opendir("/sys/class/thermal");
	struct dirent *de;
	int max_mc = 0;

	if (!d)
		return 0;

	while ((de = readdir(d))) {
		char path[PATH_MAX], buf[32];
		int fd, n;
		long mc;

		if (strncmp(de->d_name, "thermal_zone", 12))
			continue;

		snprintf(path, sizeof(path), "/sys/class/thermal/%s/temp", de->d_name);
		fd = open(path, O_RDONLY);
		if (fd < 0)
			continue;
		n = read(fd, buf, sizeof(buf) - 1);
		close(fd);
		if (n <= 0)
			continue;
		buf[n] = 0;
		mc = strtol(buf, NULL, 10);
		/* some platforms report in tenths of a degree */
		if (mc > 1000)
			mc /= 1000;
		else if (mc > 200)
			mc /= 10;
		if (mc > max_mc && mc < 150)
			max_mc = (int)mc;
	}
	closedir(d);
	return max_mc;
}

/* parse one /proc/<pid>/stat; comm may contain spaces and parens */
static int parse_stat(const char *buf, int *pid_out, char *name, size_t nlen,
		      unsigned long long *ticks, unsigned long long *rss_pages)
{
	const char *lp = strrchr(buf, ')');
	const char *p;
	unsigned long long utime = 0, stime = 0, rss = 0;
	int idx = 0, field = 3;   /* field 3 = state, right after "pid (comm) " */
	char tmp[64];

	if (!lp)
		return -1;

	p = strchr(buf, '(');
	if (!p)
		return -1;
	snprintf(name, nlen, "%.*s", (int)(lp - p - 1), p + 1);

	*pid_out = atoi(buf);

	p = lp + 2;   /* skip ") " */
	while (p && *p && field <= 24) {
		char *end;

		while (*p == ' ')
			p++;
		if (!*p)
			break;

		end = strchr(p, ' ');
		if (end) {
			snprintf(tmp, sizeof(tmp), "%.*s", (int)(end - p), p);
			p = end + 1;
		} else {
			snprintf(tmp, sizeof(tmp), "%s", p);
			p = NULL;
		}

		switch (field) {
		case 12: utime = strtoull(tmp, NULL, 10); break;   /* utime within 14/15 in raw, minus 3 offset */
		case 13: stime = strtoull(tmp, NULL, 10); break;
		case 22: rss   = strtoull(tmp, NULL, 10); break;
		}
		field++;
		idx++;
	}
	(void)idx;
	*ticks = utime + stime;
	*rss_pages = rss;
	return 0;
}

int athena_collect(unsigned long long *out_cpu_total, int *out_temp, int *out_window,
		   unsigned long long *out_mem_total_kb, unsigned long long *out_mem_used_kb,
		   unsigned long long *out_mem_proc_kb, struct pent *procs, int *out_nprocs);

/* ---- core collector: also reused by the host-side self test ---- */
int athena_collect(unsigned long long *out_cpu_total, int *out_temp, int *out_window,
		   unsigned long long *out_mem_total_kb, unsigned long long *out_mem_used_kb,
		   unsigned long long *out_mem_proc_kb, struct pent *procs, int *out_nprocs)
{
	DIR *d;
	struct dirent *de;
	struct timespec now;
	unsigned long long total = 0, idle = 0;
	unsigned long long mt = 0, ma = 0;
	unsigned long long proc_kb = 0;
	long pagesize = sysconf(_SC_PAGESIZE);
	long hz = sysconf(_SC_CLK_TCK);
	long ncpu = sysconf(_SC_NPROCESSORS_ONLN);
	double elapsed;
	int n = 0, i;

	if (pagesize <= 0) pagesize = 4096;
	if (hz <= 0)       hz = 100;
	if (ncpu <= 0)     ncpu = 1;

	clock_gettime(CLOCK_MONOTONIC, &now);

	if (read_cpu_totals(&total, &idle) < 0) {
		total = 0; idle = 0;
	}
	if (read_meminfo(&mt, &ma) < 0) {
		mt = 0; ma = 0;
	}

	elapsed = s_have_prev
		? (now.tv_sec - s_prev_ts.tv_sec) + (now.tv_nsec - s_prev_ts.tv_nsec) / 1e9
		: 0.0;

	/* CPU utilisation over the elapsed window */
	if (s_have_prev && elapsed >= 0.5 && total > s_prev_total) {
		double dt = (double)(total - s_prev_total);
		double di = (double)(idle  - s_prev_idle);

		if (di < 0) di = 0;
		if (di > dt) di = dt;
		*out_cpu_total = (unsigned long long)((dt - di) * 100.0 / dt + 0.5);
		*out_window = (int)(elapsed + 0.5);
	} else {
		*out_cpu_total = 0;
		*out_window = 0;
	}

	*out_temp = read_temp();

	/* per-process scan */
	d = opendir("/proc");
	if (d) {
		while ((de = readdir(d))) {
			char path[PATH_MAX], buf[4096];
			struct pent e;
			unsigned long long ticks = 0, rssp = 0;
			int pid, fd, rd, is_kthread = 1;
			const char *q;

			if (!isdigit((unsigned char)de->d_name[0]))
				continue;
			for (q = de->d_name; *q; q++)
				if (!isdigit((unsigned char)*q))
					break;
			if (*q)
				continue;

			pid = atoi(de->d_name);
			if (pid <= 0)
				continue;

			snprintf(path, sizeof(path), "/proc/%d/stat", pid);
			fd = open(path, O_RDONLY);
			if (fd < 0)
				continue;
			rd = read(fd, buf, sizeof(buf) - 1);
			close(fd);
			if (rd <= 0)
				continue;
			buf[rd] = 0;

			memset(&e, 0, sizeof(e));
			if (parse_stat(buf, &e.pid, e.name, sizeof(e.name), &ticks, &rssp) < 0)
				continue;

			/* kernel thread detection: empty cmdline means no user space */
			snprintf(path, sizeof(path), "/proc/%d/cmdline", pid);
			fd = open(path, O_RDONLY);
			if (fd >= 0) {
				rd = read(fd, buf, 1);
				close(fd);
				if (rd > 0)
					is_kthread = 0;
			} else {
				is_kthread = 0;   /* can't tell -> treat as normal */
			}
			if (is_kthread)
				continue;

			e.ticks  = ticks;
			e.rss_kb = rssp * (unsigned long long)pagesize / 1024ULL;
			proc_kb += e.rss_kb;

			if (n < MAX_PROCS)
				procs[n++] = e;
		}
		closedir(d);
	}

	/* per-process cpu% from the stored snapshot */
	for (i = 0; i < n; i++) {
		int j;
		procs[i].pid = procs[i].pid;   /* keep */
		if (!s_have_prev || elapsed < 0.5) {
			procs[i].ticks = 0;
			continue;
		}
		for (j = 0; j < s_prev_n; j++) {
			if (s_prev[j].pid == procs[i].pid) {
				unsigned long long dt = procs[i].ticks - s_prev[j].ticks;
				procs[i].ticks = dt;
				break;
			}
		}
		if (j == s_prev_n)
			procs[i].ticks = procs[i].ticks;   /* new process: keep absolute as rough share */
	}

	/* remember snapshot for the next call */
	for (i = 0; i < n && i < MAX_PROCS; i++)
		s_prev[i] = procs[i];
	s_prev_n = n;
	s_prev_total = total;
	s_prev_idle = idle;
	s_prev_ts = now;
	s_have_prev = 1;

	*out_mem_total_kb = mt;
	*out_mem_used_kb  = (mt > ma) ? (mt - ma) : 0;
	*out_mem_proc_kb  = proc_kb;
	*out_nprocs = n;

	(void)hz; (void)ncpu;
	return 0;
}
