(function(){
  /* CSC 16avos MIXTO+120'. CUPO = nº de ANDRES BORRERO (1..5). Cambia y re-pega. NO envía. */
  var CUPO = 4;  // <<<<<< 4=ancla(B4) · 1,2=perturbados · 3,5=lotería
  var PART = [{"L": "Sudáfrica", "V": "Canadá", "aL": ["sudafrica", "southafrica"], "aV": ["canada"], "s": [[1, 2], [1, 2], [1, 3], [1, 2], [0, 2]]}, {"L": "Brasil", "V": "Japón", "aL": ["brasil", "brazil"], "aV": ["japon", "japan"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [2, 0]]}, {"L": "Alemania", "V": "Paraguay", "aL": ["alemania", "germany"], "aV": ["paraguay"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [2, 0]]}, {"L": "Países Bajos", "V": "Marruecos", "aL": ["paisesbajos", "netherlands", "holanda"], "aV": ["marruecos", "morocco"], "s": [[2, 1], [2, 1], [1, 1], [2, 1], [3, 1]]}, {"L": "Costa de Marfil", "V": "Norway", "aL": ["costademarfil", "ivorycoast"], "aV": ["noruega", "norway"], "s": [[1, 2], [1, 2], [1, 1], [1, 2], [1, 3]]}, {"L": "Francia", "V": "Sweden", "aL": ["francia", "france"], "aV": ["suecia", "sweden"], "s": [[3, 1], [3, 1], [3, 1], [2, 1], [4, 1]]}, {"L": "México", "V": "Ecuador", "aL": ["mexico"], "aV": ["ecuador"], "s": [[1, 1], [1, 1], [1, 1], [2, 1], [1, 0]]}, {"L": "Inglaterra", "V": "DR Congo", "aL": ["inglaterra", "england"], "aV": ["congo", "drcongo", "rdcongo"], "s": [[2, 1], [2, 1], [2, 0], [2, 1], [3, 1]]}, {"L": "Bélgica", "V": "Senegal", "aL": ["belgica", "belgium"], "aV": ["senegal"], "s": [[2, 1], [2, 1], [1, 1], [2, 1], [3, 1]]}, {"L": "USA", "V": "Bosnia & Herzegovina", "aL": ["usa", "estadosunidos", "unitedstates", "eeuu"], "aV": ["bosnia", "bosniaherzegovina"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [2, 0]]}, {"L": "España", "V": "Austria", "aL": ["espana", "spain"], "aV": ["austria"], "s": [[2, 0], [2, 1], [2, 0], [2, 1], [3, 1]]}, {"L": "Portugal", "V": "Croacia", "aL": ["portugal"], "aV": ["croacia", "croatia"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [1, 1]]}, {"L": "Suiza", "V": "Algeria", "aL": ["suiza", "switzerland"], "aV": ["argelia", "algeria"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [1, 1]]}, {"L": "Australia", "V": "Egipto", "aL": ["australia"], "aV": ["egipto", "egypt"], "s": [[1, 2], [1, 2], [1, 1], [1, 2], [2, 1]]}, {"L": "Argentina", "V": "Cape Verde", "aL": ["argentina"], "aV": ["caboverde", "capeverde"], "s": [[2, 1], [2, 0], [2, 0], [2, 1], [3, 1]]}, {"L": "Colombia", "V": "Ghana", "aL": ["colombia"], "aV": ["ghana"], "s": [[2, 1], [2, 1], [2, 0], [2, 1], [3, 1]]}];
  function k(s){return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}
  function has(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return t.indexOf(al[i]);}return -1;}
  function setVal(el,v){el.value=v;["input","change","blur"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}
  var inputs=[].slice.call(document.querySelectorAll("input[type=number],input[type=text],input:not([type])"));
  var conts=[],seen=[];
  inputs.forEach(function(inp){var n=inp;for(var u=0;u<7&&n;u++){n=n.parentElement;if(!n)break;
    if(n.querySelectorAll("input[type=number],input[type=text],input:not([type])").length>=2){if(seen.indexOf(n)<0){seen.push(n);conts.push(n);}break;}}});
  var ok=0,miss=[];
  PART.forEach(function(p){var done=false;
    for(var c=0;c<conts.length;c++){var t=k(conts[c].textContent);var iL=has(t,p.aL),iV=has(t,p.aV);
      if(iL>=0&&iV>=0){var ins=conts[c].querySelectorAll("input[type=number],input[type=text],input:not([type])");if(ins.length<2)continue;
        var rev=iV<iL,gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];setVal(ins[0],rev?gv:gl);setVal(ins[1],rev?gl:gv);ok++;done=true;break;}}
    if(!done)miss.push(p.L+" vs "+p.V);});
  console.log("%cCSC ANDRES BORRERO "+CUPO+": llené "+ok+"/"+PART.length,"font-size:14px;color:"+(ok==PART.length?"green":"orange"));
  if(miss.length)console.warn("FALTAN (a mano):",miss);
  console.log("Revisa y dale ENVIAR tú. Cambia CUPO y re-pega para el siguiente.");
})();