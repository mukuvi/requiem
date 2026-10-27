#include <stdio.h>

int main(void) {
    int *p = 0;
    printf("About to dereference...\n");
    *p = 42;
    printf("Never reached\n");
    return 0;
}
