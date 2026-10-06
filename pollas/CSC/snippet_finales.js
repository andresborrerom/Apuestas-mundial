(function(){
  /* CSC FINALES A_hedge (auditada) (3er puesto + final). Llena EMAIL + CUPO (numero) + marcadores. NO envía. */
  var CUPO = 1;  // <<<<<< cambia 1..5 y re-pega. B1:1-2/1-0 · B2:1-2/2-1 · B3:1-2/1-2 · B4:3-1/2-1 · B5:2-1/1-2
  var EMAIL = "andres.borrerom@gmail.com";
  var PART = [{"L": "Francia", "V": "Inglaterra", "aL": ["francia", "france"], "aV": ["inglaterra", "england"], "s": [[1, 2], [1, 2], [1, 2], [3, 1], [2, 1]]}, {"L": "España", "V": "Argentina", "aL": ["espana", "spain"], "aV": ["argentina"], "s": [[1, 0], [2, 1], [1, 2], [2, 1], [1, 2]]}];
  var MAXLAB = 80;   // un ancla de partido debe ser un elemento corto (título), no un contenedor
  function k(s){return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]/g,"");}
  function hasA(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return true;}return false;}
  function setVal(el,v){el.value=v;["input","change","blur","keyup"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}
  var used=[];
  var allIn=[].slice.call(document.querySelectorAll("input,textarea")).filter(function(i){return i.type!=="hidden";});
  var inputs=allIn.filter(function(i){return i.type!=="email";});
  var els=[].slice.call(document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,p,label,td,li,b,strong"));
  function anchorInput(keywords){
    var lab=null,len=1e9;
    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");if(!t||t.length>MAXLAB)continue;
      for(var j=0;j<keywords.length;j++){if(t.indexOf(keywords[j])>=0){var L=t.length;if(L<len){len=L;lab=els[i];}break;}}}
    if(!lab)return null;
    var inside=allIn.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});
    if(inside.length)return inside[0];
    var foll=allIn.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});
    return foll.length?foll[0]:null;
  }
  /* 1) EMAIL */
  var emEl=allIn.filter(function(i){return i.type==="email";})[0]||anchorInput(["correoelectronico","correo","email"]);
  if(emEl){setVal(emEl,EMAIL);used.push(emEl);}
  /* 2) CUPO (cajita numérica; si no, campo de nombre) */
  var cupoEl=anchorInput(["cupo"]);
  if(cupoEl){setVal(cupoEl,CUPO);used.push(cupoEl);}
  else{var nomEl=anchorInput(["nombreyapellido","nombrecompleto","nombre","participante"]);
       if(nomEl){setVal(nomEl,"ANDRES BORRERO "+CUPO);used.push(nomEl);cupoEl=nomEl;}}
  /* 3) MARCADORES — ancla CORTA con AMBOS equipos (rechaza contenedores) */
  var ok=0,miss=[],log=[];
  PART.forEach(function(p){
    var lab=null,len=1e9;
    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");
      if(t.length<=MAXLAB&&hasA(t,p.aL)&&hasA(t,p.aV)){var L=t.length;if(L<len){len=L;lab=els[i];}}}
    if(!lab){miss.push(p.L+" vs "+p.V);return;}
    var cand2=inputs.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});
    if(cand2.length!==2){cand2=inputs.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});}
    if(cand2.length<2){miss.push(p.L+" vs "+p.V);return;}
    var gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];
    setVal(cand2[0],gl);setVal(cand2[1],gv);used.push(cand2[0],cand2[1]);ok++;
    log.push("   "+p.L+" "+gl+"-"+gv+" "+p.V);
  });
  /* 4) RESUMEN */
  if(ok===0){console.log("%c🛑 ESTE FORM NO PARECE SER DE FINALES (no encontré Francia-Inglaterra ni España-Argentina como partidos). NO ENVÍES NADA. Recarga la página.","font-size:16px;font-weight:bold;color:white;background:red;padding:4px 10px");return;}
  var idok=(emEl?"✉️ "+EMAIL:"✉️ ⚠️ EMAIL a mano")+"  ·  "+(cupoEl?"🎫 CUPO = "+CUPO:"🎫 ⚠️ CUPO NO ENCONTRADO — escríbelo a mano");
  console.log("%c══ VAS A ENVIAR EL CUPO "+CUPO+" ══","font-size:20px;font-weight:bold;color:white;background:"+(ok==PART.length&&emEl&&cupoEl?"green":"darkorange")+";padding:4px 10px");
  console.log("%c"+idok,"font-size:14px;font-weight:bold");
  console.log("%cMarcadores "+ok+"/"+PART.length+":\n"+log.join("\n"),"font-size:13px");
  if(miss.length)console.warn("FALTAN (a mano):",miss);
  console.log("%cVERIFICA en pantalla: cajita Cupo = "+CUPO+" y los marcadores en los partidos CORRECTOS.","font-size:13px;color:orange;font-weight:bold");
})();