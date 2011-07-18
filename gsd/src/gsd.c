
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <libgen.h>


static uint8_t verbose_flag = 0;
static uint8_t daemon_flag = 0;
static char *frontend = 0;
static char *backend = 0;
static int min_worker = 1;
static int max_worker = 32;
static int spare_worker = 8;
static int heartbeat_interval = 1000;


void usage(char *prog) {
    const char *format = \
"usage: %s [options] <worker command line>\n"
"\n"
"options:\n"
"    -h, --help\n"
"        Show this help message\n"
"\n"
"    -f <endpoint>, --frontend=<endpoint>\n"
"        The binding endpoints where clients will connect to\n"
"        [default: tcp://*:5000]\n"
"\n"
"    -b <endpoint>, --backend=<endpoint>\n"
"        The binding endpoints where workers will connect to\n"
"        [default: ipc://tmp/(pid-of-gsd).ipc]\n"
"\n"
"    -n, --min-worker=<num>\n"
"        The mininum number of workers should be started before accepting \n"
"        request [default: 1]\n"
"\n"
"    -x, --max-worker=<num> \n"
"        The maxinum number of workers [default: 32]\n"
"\n"
"    -s, --spare-worker=<num>\n"
"        The number of spare workers [default: 8]\n"
"\n"
"    -i, --hearbeat-interval=<milliseconds>\n"
"        Heartbeat interval in millisecond [default: 1000]\n"
"\n"
"    -d, --daemon\n"
"\n"
"    -v, --verbose\n"
"\n";

    printf(format, basename(prog));
    exit(2);
};

int parse_argv(int argc, char **argv) {
    struct option longopts[] = {
        {"help",               no_argument,       0, 'h'},
        {"frontend",           required_argument, 0, 'f'},
        {"backend",            required_argument, 0, 'b'},
        {"min-worker",         required_argument, 0, 'n'},
        {"max-worker",         required_argument, 0, 'x'},
        {"spare-worker",       required_argument, 0, 's'},
        {"heartbeat-interval", required_argument, 0, 'i'},
        {"daemon",             no_argument,       0, 'd'},
        {"verbose",            no_argument,       0, 'v'},
        {0, 0, 0, 0}
    };

    int c;
    int indexptr = 0;

    while ((c = getopt_long(argc, argv, "hf:b:n:x:s:i:dv", longopts, &indexptr)) != -1) {
        switch (c) {
        case 0:
            break;

        case 'h':
            usage(argv[0]);
            break;

        case 'f':
            printf("frontend: %s\n", optarg);
            break;

        case 'b':
            printf("backend: %s\n", optarg);
            break;

        case 'n':
            printf("min-worker: %s\n", optarg);
            break;

        case 'x':
            printf("max-worker: %s\n", optarg);
            break;

        case 's':
            printf("spare-worker: %s\n", optarg);
            break;

        case 'i':
            printf("heartbeat-interval: %s\n", optarg);
            break;            

        case 'd':
            printf("daemon\n");
            break;    

        case 'v':
            printf("verbose\n");
            break;                

        case '?':
            break;

        defalut:
            abort();
        }
    }

    if (optind < argc) {
        printf("worker-command-line: ");
        while (optind < argc) {
            printf("%s ", argv[optind++]);
        }
        printf("\n");
    }
}

int main(int argc, char **argv) {
    printf("%s\n\n", "Generic Service Daemon");
    parse_argv(argc, argv);
    exit(0);
}

