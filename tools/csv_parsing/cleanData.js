/*
 * This file is deprecated and should be removed
 */

let fs = require('fs');
let files = fs.readdirSync('converted');
//files = ['#6.json'];

//let out = '';
//console.log(decodeURIComponent(escape()));
for(let file of files) {
  console.log(file);
  let lines = fs.readFileSync('converted/'+file, 'UTF-8').toString().split("\n");
  let i = 0;
  for(let line of lines) {
    let item = line.split('": "');
    if(item.length > 1) {

      let tmp = item[1].split("u00").join("\\u00");
     /*  console.log(tmp);
      tmp = tmp.replace(/[\u00A0\u1680​\u180e\u2000-\u2009\u200a​\u200b​\u202f\u205f​\u3000]/g,''); */
      tmp = escape(tmp);
      let value;
      let k;
      try {
        k = decodeURIComponent(escape(item[0])).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      }
      catch(e) {
        k = item[0];
      }
      try {
        value = decodeURIComponent(tmp).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      }
      catch(e) {
        value = item[1];
      }
      lines[i] = k+'": "'+value;
    }
    i++;
  }
  JSON.parse(lines.join("\n"));
  fs.writeFileSync("newConverted/"+file, lines.join("\n"));
}




