#! /bin/bash

version="0.0.9"

thisdir=$(pwd)
scriptdir=$( (cd `dirname $0` && echo $PWD) )
basedir=$(dirname $(dirname ${scriptdir}))

while test -n "$1"; do
  case $1 in
    "-tag")
      tag=$2
      shift
      ;;
    "-destdir")
      destdir=$2
      shift
      ;;
    *)
      echo "Usage: $(basename $0) [-tag tag] [-destdir /destination/for/file.tar.gz]" 
      exit
      ;;
  esac
  shift
done

if test -z "${destdir}"; then
  destdir="${thisdir}"
fi

tardir="tarball${RANDOM}"

mkdir ${tardir}
cd ${tardir}
  ln -s ${basedir}/wn/* .
  tar czhv --exclude=".svn" \
    --exclude="WPS" --exclude="WRFV3" --exclude="openmpi" \
    -f ${destdir}/WRF4G-${version}${tag}.tar.gz *
cd ..
rm -rf ${tardir}
