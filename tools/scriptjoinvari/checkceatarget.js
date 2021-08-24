var fs = require('fs');
 
var cea = fs.readFileSync('CEA_Round2_Targets.csv', 'utf8').split('\n');
var target = fs.readFileSync('CTA_Round2_Targets.csv', 'utf8').split('\n');
var t = [];
for(var i=0;i<target.length-1;i++){
	t[target[i]]=true;
}

var tmps='';

for(var i=0;i<cea.length-1;i++){ //
	var s = cea[i].split('","');
	var s1 = s[0]+'","'+s[1]+'"';
	if(!t[s1]){
		console.log(s1);
		tmps+=s1+'\n';
	}
}
//console.log(tmps);
fs.appendFile('ceaTarget.csv', tmps, function (err) {
		  if (err) throw err;
		});