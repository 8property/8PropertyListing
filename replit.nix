{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.python311Packages.selenium
    pkgs.chromium
    pkgs.chromedriver
    pkgs.glibcLocales
    pkgs.freetype
    pkgs.fontconfig
  ];
}

