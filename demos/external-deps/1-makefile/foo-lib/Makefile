
UNAME := $(shell uname)

CC = clang
AR = ar
CFLAGS = -Wall -fPIC
ifeq ($(UNAME),Darwin)
	SHAREDLIB_LDFLAGS := -dynamiclib
else
	SHAREDLIB_LDFLAGS := -shared
endif

BUILDROOT = _build_

SRC  = fooutil.c
DEPS = fooutil.h
OBJS = $(SRC:.c=.o)
ifeq ($(UNAME),Darwin)
	TARGET_SO := libfooutil.dylib
else
	TARGET_SO := libfooutil.so
endif
TARGET_A  = libfooutil.a

# debug
DEBUG_BUILDOUT = $(BUILDROOT)/debug
DEBUG_TARGET_SO = $(DEBUG_BUILDOUT)/$(TARGET_SO)
DEBUG_TARGET_A = $(DEBUG_BUILDOUT)/$(TARGET_A)
DEBUG_OBJS = $(addprefix $(DEBUG_BUILDOUT)/, $(OBJS))
DEBUG_CFLAGS = -O0 -g

# release
RELEASE_BUILDOUT = $(BUILDROOT)/release
RELEASE_TARGET_SO = $(RELEASE_BUILDOUT)/$(TARGET_SO)
RELEASE_TARGET_A = $(RELEASE_BUILDOUT)/$(TARGET_A)
RELEASE_OBJS = $(addprefix $(RELEASE_BUILDOUT)/, $(OBJS))
RELEASE_CFLAGS = -O2

.PHONY: all prep clean debug release cleandebug cleanrelease

all: release

debug: BUILDOUT = $(DEBUG_BUILDOUT)
debug: prep $(DEBUG_TARGET_SO) $(DEBUG_TARGET_A)

release: BUILDOUT = $(RELEASE_BUILDOUT)
release: prep $(RELEASE_TARGET_SO) $(RELEASE_TARGET_A)

$(DEBUG_TARGET_SO): $(DEBUG_OBJS)
	$(CC) $(CFLAGS) $(DEBUG_CFLAGS) $(SHAREDLIB_LDFLAGS) -o $@ $^

$(DEBUG_TARGET_A): $(DEBUG_OBJS)
	$(AR) rcs $@ $^

$(DEBUG_BUILDOUT)/%.o: %.c $(DEPS)
	$(CC) -c $(CFLAGS) $(DEBUG_CFLAGS) -o $@ $<

$(RELEASE_TARGET_SO): $(RELEASE_OBJS)
	$(CC) $(CFLAGS) $(RELEASE_CFLAGS) $(SHAREDLIB_LDFLAGS) -o $@ $^

$(RELEASE_TARGET_A): $(RELEASE_OBJS)
	$(AR) rcs $@ $^

$(RELEASE_BUILDOUT)/%.o: %.c $(DEPS)
	$(CC) -c $(CFLAGS) $(RELEASE_CFLAGS) -o $@ $<

prep:
	@mkdir -p $(BUILDOUT)

clean:
	rm -fr $(BUILDROOT)

cleandebug:
	rm -fr $(DEBUG_BUILDOUT)

cleanrelease:
	rm -fr $(RELEASE_BUILDOUT)
