from distutils.core import setup
setup(
  name = 'trieste',
  packages = ['trieste'],
  version = '0.1.0',
  description = 'A library for creating and reading Trieste archives.',
  author = 'Nathaniel R. Stickley',
  author_email = 'nathaniel.stickley@gmail.com',
  url = 'https://github.com/nrstickley/trieste',
  download_url = 'https://github.com/nrstickley/trieste/archive/0.1.tar.gz',
  keywords = ['archive', 'forensic', 'interchange'], 
  classifiers = [],
  python_requires='~=3.6',
  install_requires=['numpy']
)
