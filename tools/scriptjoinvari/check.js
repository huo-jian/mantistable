var fs = require('fs');
 
var it = fs.readFileSync('CTA2.csv', 'utf8').split('\n');
var target = fs.readFileSync('CTA_Round2_Targets.csv', 'utf8').split('\n');
var t = [];
for(var i=0;i<target.length-1;i++){
	t[target[i]]=true;
}

var ar=[];
var tmps=''
for(var i=0;i<it.length-1;i++){ //
	var s = it[i].split('","');
	var ss = s[0]+'","'+s[1]+'"';
	if(!t[ss]){
		console.log(ss);
	}else{
		t[ss]=false;
		//s=s.join('","');
		tmps+=s[0]+'\n';
	}
}
var a=[];
for(var i in t){
	if(t[i]==true)
		a.push(i.split('","')[0].substr(1));
}
console.log(JSON.stringify(a));
/*fs.appendFile('newCTA.csv', tmps, function (err) {
		  if (err) throw err;
		});*/