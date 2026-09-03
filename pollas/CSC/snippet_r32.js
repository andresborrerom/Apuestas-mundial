(function(){
  var CUPO = 1;  /* <<<<<< 1..5 = ANDRES BORRERO N */
  var PART = [{"L": "Sudáfrica", "V": "Canadá", "aL": ["sudafrica", "southafrica"], "aV": ["canada"], "s": [[1, 2], [1, 2], [1, 3], [1, 2], [0, 2]]}, {"L": "Brasil", "V": "Japón", "aL": ["brasil", "brazil"], "aV": ["japon", "japan"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [2, 0]]}, {"L": "Alemania", "V": "Paraguay", "aL": ["alemania", "germany"], "aV": ["paraguay"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [2, 0]]}, {"L": "Países Bajos", "V": "Marruecos", "aL": ["paisesbajos", "netherlands", "holanda"], "aV": ["marruecos", "morocco"], "s": [[2, 1], [2, 1], [1, 1], [2, 1], [3, 1]]}, {"L": "Costa de Marfil", "V": "Norway", "aL": ["costademarfil", "ivorycoast"], "aV": ["noruega", "norway"], "s": [[1, 2], [1, 2], [1, 1], [1, 2], [1, 3]]}, {"L": "Francia", "V": "Sweden", "aL": ["francia", "france"], "aV": ["suecia", "sweden"], "s": [[3, 1], [3, 1], [3, 1], [2, 1], [4, 1]]}, {"L": "México", "V": "Ecuador", "aL": ["mexico"], "aV": ["ecuador"], "s": [[1, 1], [1, 1], [1, 1], [2, 1], [1, 0]]}, {"L": "Inglaterra", "V": "DR Congo", "aL": ["inglaterra", "england"], "aV": ["congo", "drcongo", "rdcongo"], "s": [[2, 1], [2, 1], [2, 0], [2, 1], [3, 1]]}, {"L": "Bélgica", "V": "Senegal", "aL": ["belgica", "belgium"], "aV": ["senegal"], "s": [[2, 1], [2, 1], [1, 1], [2, 1], [3, 1]]}, {"L": "USA", "V": "Bosnia & Herzegovina", "aL": ["usa", "estadosunidos", "unitedstates", "eeuu"], "aV": ["bosnia", "bosniaherzegovina"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [2, 0]]}, {"L": "España", "V": "Austria", "aL": ["espana", "spain"], "aV": ["austria"], "s": [[2, 0], [2, 1], [2, 0], [2, 1], [3, 1]]}, {"L": "Portugal", "V": "Croacia", "aL": ["portugal"], "aV": ["croacia", "croatia"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [1, 1]]}, {"L": "Suiza", "V": "Algeria", "aL": ["suiza", "switzerland"], "aV": ["argelia", "algeria"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [1, 1]]}, {"L": "Australia", "V": "Egipto", "aL": ["australia"], "aV": ["egipto", "egypt"], "s": [[1, 2], [1, 2], [1, 1], [1, 2], [2, 1]]}, {"L": "Argentina", "V": "Cape Verde", "aL": ["argentina"], "aV": ["caboverde", "capeverde"], "s": [[2, 1], [2, 0], [2, 0], [2, 1], [3, 1]]}, {"L": "Colombia", "V": "Ghana", "aL": ["colombia"], "aV": ["ghana"], "s": [[2, 1], [2, 1], [2, 0], [2, 1], [3, 1]]}];
  function k(s){return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}
  function hasA(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return true;}return false;}
  function setVal(el,v){el.value=v;["input","change","blur","keyup"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}
  var inputs=[].slice.call(document.querySelectorAll("input")).filter(function(i){return i.type!=="email"&&i.type!=="hidden";});
  if(inputs.length<10){console.log("%c⚠️ CONTEXTO EQUIVOCADO: arriba-izq de la consola, en el dropdown elige userHtmlFrame (userCodeAppPanel) y vuelve a pegar.","font-size:16px;font-weight:bold;color:red");return;}
  var els=[].slice.call(document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,p,label,td,li,b,strong"));
  var used=[],ok=0,miss=[],log=[];
  PART.forEach(function(p){
    var lab=null,len=1e9;
    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");
      if(hasA(t,p.aL)&&hasA(t,p.aV)){var L=(els[i].textContent||"").length;if(L<len){len=L;lab=els[i];}}}
    if(!lab){miss.push(p.L+" vs "+p.V);return;}
    var inside=inputs.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});
    var foll=inputs.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});
    var cand=(inside.length===2)?inside:foll;
    if(cand.length<2){miss.push(p.L+" vs "+p.V);return;}
    var gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];
    setVal(cand[0],gl);setVal(cand[1],gv);used.push(cand[0],cand[1]);ok++;
    log.push(p.L+" "+gl+"-"+gv+" "+p.V);
  });
  console.log("%cCSC BORRERO "+CUPO+": llené "+ok+"/"+PART.length,"font-size:15px;font-weight:bold;color:"+(ok==PART.length?"green":"orange"));
  console.log(log.join("\n"));
  if(miss.length)console.warn("FALTAN (a mano):",miss);
})();