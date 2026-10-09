pkgname=campermit
pkgver=0.1.0
pkgrel=1
pkgdesc="Linux command-line utility to enable and disable USB webcams"
arch=('any')
url="https://github.com/gouthamkrishnap/campermit"
license=('MIT')
depends=('python')
makedepends=('git' 'python-build' 'python-installer' 'python-setuptools')

_commit=9ed0683f20a3c5d7d99bf81ff4bb8aed37afa3ca
source=("campermit::git+https://github.com/gouthamkrishnap/campermit.git#commit=$_commit")
sha256sums=('SKIP')

build() {
    cd "$srcdir/campermit"
    /usr/bin/python -m build --wheel
}

package() {
    cd "$srcdir/campermit"
    /usr/bin/python -m installer --destdir="$pkgdir" dist/*.whl
}
