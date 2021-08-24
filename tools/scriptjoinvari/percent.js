var fs = require('fs');
 
var it = fs.readFileSync('z.info_table.json', 'utf8').split('\n');
var an = JSON.parse(fs.readFileSync('T2Dv2.json', 'utf8'));

var counteq=0;
var coundiversi=0;

for(var i =0;i<it.length;i++){ //
	var tmp = JSON.parse(it[i]);
	if(!tmp["subCol"])
		tmp["subCol"]=0;
	if(tmp["subCol"]==an[i]["subCol"])
		counteq++;
	else
		coundiversi++;
}

console.log(counteq*100/234);
//console.log(coundiversi);