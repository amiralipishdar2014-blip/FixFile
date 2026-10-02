TERMUX_PKG_HOMEPAGE=https://github.com/amiralipishdar2014-blip/FixFile
TERMUX_PKG_DESCRIPTION="AI-powered code repair tool for Termux"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="amiralipishdar2014-blip"
TERMUX_PKG_VERSION=1.0.0
TERMUX_PKG_SRCURL=https://github.com/amiralipishdar2014-blip/FixFile/archive/refs/heads/main.tar.gz
TERMUX_PKG_SHA256=SKIP

termux_step_make_install() {
    install -Dm755 "$TERMUX_PKG_SRCDIR/fixfile.py" \
        "$TERMUX_PREFIX/bin/fixfile"
}
