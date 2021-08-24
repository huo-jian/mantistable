var fs = require('fs');
 
var cpa = fs.readFileSync('CPA_Round2_Targets.csv', 'utf8').split('\n');
var target = fs.readFileSync('CTA_Round2_Targets.csv', 'utf8').split('\n');
var t = [];
for(var i=0;i<target.length-1;i++){
	t[target[i]]=true;
}

var ar=[];
var tmps='';
var altritarget='';
var oldvalue='';
var enter=false;
for(var i=0;i<cpa.length-1;i++){ //
	var s = cpa[i].split('","');
	if(oldvalue!=s[0]){
		oldvalue=s[0];
		enter=false;
	}
	var s1 = s[0]+'","'+s[1]+'"';
	var s2 = s[0]+'","'+s[2];
	if(!t[s1]&&!enter){
		console.log(s1);
		altritarget+=s1+'\n';
		enter=true;
	}else if(!t[s2]){
		console.log(s2);
		//altritarget+=s2+'\n';
	}else{
		s=s.join('","');
		tmps+=s+'\n';
	}
}
//console.log(tmps);
fs.appendFile('newTarget.csv', altritarget, function (err) {
		  if (err) throw err;
		});