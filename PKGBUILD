# Maintainer: Robert Holt <rholt@datto.com>

pkgname=pacman-plugin-spacewalk
pkgver=1.0.0
pkgrel=1
pkgdesc="Plugin for spacewalk that adds pacman support"
arch=('any')
url="https://github.com/rob356/pacman-plugin-spacewalk"
license=('GPL')
depends=('python' 'pyalpm' 'rhn-client-tools')
source=('packages.py')
md5sums=('57313f05f55038f06d5b99833067bb3d')

package() {
  install -D "${srcdir}/packages.py" "${pkgdir}/usr/lib/python3.6/rhn/actions/packages.py"
}
