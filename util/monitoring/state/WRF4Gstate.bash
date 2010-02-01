#!/bin/bash 
leave_initial_words () {
  Fisrt_ok_word=$1
  forest_home=$2
  echo $* > ./sentence.inf
  Nwords=$#
  iword=`expr $1 + 2`
  new_sentence=''
  while test ${iword} -le ${Nwords}
  do
  new_word=`awk -f ${foresthome}/AWK/column.awk row=1 col=${iword} ./sentence.inf`
  new_sentence=${new_sentence}' '${new_word}
  iword=`expr ${iword} + 1`
### End number of words
  done 
  echo ${new_sentence}
  rm  ./sentence.inf
}

#######   #######    #######   #######    #######    #######    ###### 
   #######    #######   #######    #######    #######    ###### 
if test $1 = '-h'
then
echo "*************************"
echo "*** Shell to evaluate ***"
echo "*** WRF4G simulations ***"
echo "***       state       ***"
echo "*************************"
echo "WRF4Gstatte.bash"
else
foresthome='/oceano/gmeteo/users/lluis'
rootsh='/oceano/gmeteo/users/lluis/estudios/www'

cd ${rootsh}
outfile='WRF4Gstate_experiments.inf'
rm ${rootsh}/${outfile} >& /dev/null

##leave_initial_words 2 ${foresthome} `head -n 2 ${rootsh}/WRF4G_running_places.inf | tail -n 1`

now=`date +%Y-%m-%d_%H:%M:%S`
rm ${rootsh}/WRF4Gcauses.inf 

(
cat << EOF
<HTML>
<head>
<link rel="stylesheet" type="text/css" href="WRF4Gstate.css" />
<link rel="shortcut icon" href="wrf4g_sq_32x32.png" />
<title>state of WRF4G experiments</title>
</head>
<body>
<div class="title">
<img src="wrf4gp.png"></img>
<b>WRF4G experiments' state on ${now}</b>
</div>
<div class="notsuccess">
<iframe src=empty.html name="notsuccess" frameborder="0" width="100%" height="100%"></iframe>
</div>
<div class="notdone">
<iframe src=empty.html name="notfinished" frameborder="0" width="100%" height="100%"></iframe>
</div>
<div class="errs">
<iframe src=empty.html name="rslerrors" frameborder="0" width="100%" height="100%"></iframe>
</div>
<div class="outs">
<iframe src=empty.html name="rslouts" frameborder="0" width="100%" height="100%"></iframe>
</div>
<div class="experiments">
<table>
<tr><th>experiment</th><th></th><th>% done</th><th></th><th>not done</th><th>not succ.</th><th> </th><th>not rsl</th><th></th></tr>
EOF
) > ${rootsh}/WRF4Gstate.html

echo "##WRF4G experiments on "${now} > ${rootsh}/${outfile}
if test -f experiments_WRF4G.inf
then
  Nrunning=`qstat | grep lluis | grep R | wc -l`
  Nwaitting=`qstat | grep lluis | grep W | wc -l`
  echo "<tr><td>${HOSTNAME}</td><td align="center">N. sim run/wait:</td><td>${Nrunning}/${Nwaitting}</td><td> </td><td> </td><td> </td><td> </td><td> </td><td> </td></tr>" >> ${rootsh}/WRF4Gstate.html 
  cat experiments_WRF4G.inf | awk '{print $2}' >> ${rootsh}/${outfile} 
  Nexp=`wc -l experiments_WRF4G.inf | awk '{print $1}'`
  iexp=1
  while test ${iexp} -le ${Nexp}
  do
    irow=`expr 26 + ${iexp}`
    awk -f ${HOME}/AWK/line.awk row=${irow} ${rootsh}/WRF4Gcauses.html >> ${rootsh}/WRF4Gstate.html
    iexp=`expr ${iexp} + 1`
### End of local experiments
  done
fi

# External experiments
##
Nextplaces=`wc -l ${rootsh}/WRF4G_running_places.inf | awk '{print $1}'`
Nextplaces=`expr ${Nextplaces} / 3`
extfiles='experiments_WRF4G.inf WRF4Gcauses.inf WRF4Gcauses.html'
iplace=1
while test ${iplace} -le ${Nextplaces}
do
  user=`awk -f ${foresthome}/AWK/column.awk row=${iplace} col=1 ${rootsh}/WRF4G_running_places.inf` 
  machine=`awk -f ${foresthome}/AWK/column.awk row=${iplace} col=2 ${rootsh}/WRF4G_running_places.inf` 
  place=`awk -f ${foresthome}/AWK/column.awk row=${iplace} col=3 ${rootsh}/WRF4G_running_places.inf` 
  ir=`expr ${iplace} + 1`
  iw=`expr ${iplace} + 2`
  running=`leave_initial_words 2 ${foresthome} $(awk -f ${foresthome}/AWK/column.awk row=${ir} ${rootsh}/WRF4G_running_places.inf)`
  waitting=`leave_initial_words 2 ${foresthome} $(awk -f ${foresthome}/AWK/column.awk row=${iw} ${rootsh}/WRF4G_running_places.inf)`
  Nrunning=`ssh ${user}@${machine} ${running} | wc -l` 
  Nwaitting=`ssh ${user}@${machine} ${waitting} | wc -l` 
  echo "<tr><td>${machine}</td><td align="center"> N. sim run/wait:</td><td>${Nrunning}/${Nwaitting}</td><td> </td><td> </td><td> </td><td> </td><td> </td><td> </td></tr>" >> ${rootsh}/WRF4Gstate.html 

  for file in ${extfiles}
  do 
    rsync -va ${user}@${machine}:${place}/${file} ${rootsh}/${machine}_${file}
### End copying general external files
  done
  numexp_ext=`wc -l ${rootsh}/${machine}_experiments_WRF4G.inf | awk '{print $1}'`
  iexp=1
  while test ${iexp} -le ${numexp_ext}
  do
    irow=`expr 26 + ${iexp}`
    extexp=`awk -f ${foresthome}/AWK/column.awk row=${iexp} col=2 ${rootsh}/${machine}_experiments_WRF4G.inf`
    echo ${extexp} >> ${rootsh}/${outfile}
    rm ${rootsh}/'*'${extexp}'*' >& /dev/null
    rsync -va ${user}@${machine}:${place}/'*'${extexp}'*' ${rootsh}
    awk -f ${HOME}/AWK/line.awk row=${irow} ${rootsh}/${machine}_WRF4Gcauses.html >> ${rootsh}/WRF4Gstate.html
    iexp=`expr ${iexp} + 1`
### End of number of external experiments
  done 
  iplace=`expr ${iplace} + 3`
### End external places
done
(
cat << EOF
</table>
<!--meteo4g statistics. space left: ${left} occupied percentage: ${percen}-->
</div>
</body>
</HTML>
EOF
) >> ${rootsh}/WRF4Gstate.html

fi
