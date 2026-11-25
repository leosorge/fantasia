const {questions}=JSON.parse(document.getElementById("data").textContent);
const canvas=document.getElementById("course");
const ctx=canvas.getContext("2d");
const byId=id=>document.getElementById(id);
const W=canvas.width,H=canvas.height;
const planes={A:{y:347,label:"Sotto"},B:{y:239,label:"Superficie"},C:{y:131,label:"Sopra"}};
const markers=[435,995,1555];
const finish=1990;
const tokenPositions=markers.flatMap(marker=>[marker+115,marker+142,marker+169]);
const collected=new Set();
const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
let x,y,jumpY,velocity,stage,score,mode,branch,branchTime,last,selected,feedback;
function rect(color,x,y,w,h){ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),w,h);}
function path(x0,y0,x1,y1,color,width){
  ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();
  ctx.moveTo(x0,y0);ctx.lineTo(x1,y1);ctx.stroke();
}
function label(text,x,y,size,color="#291b20",align="left"){
  ctx.fillStyle=color;ctx.font="900 "+size+"px system-ui";ctx.textAlign=align;ctx.fillText(text,x,y);
}
function wrap(text,x,y,maxWidth){
  let line="";
  ctx.font="900 15px system-ui";
  for(const word of text.split(/\s+/)){
    const next=line?line+" "+word:word;
    if(line&&ctx.measureText(next).width>maxWidth){label(line,x,y,15);y+=18;line=word;}
    else line=next;
  }
  if(line)label(line,x,y,15);
}
function hud(){
  byId("hud").textContent="Domande "+stage+"/3  ·  Corrette "+score+"/3  ·  Monete "+collected.size;
}
function control(host,text,fn,labelText){
  const button=document.createElement("button");
  button.type="button";button.textContent=text;button.onclick=fn;
  if(labelText)button.setAttribute("aria-label",labelText);
  host.append(button);
}
function overlay(title,copy,action){
  const gate=byId("gate");gate.hidden=false;gate.replaceChildren();
  const h=document.createElement("h2");h.textContent=title;
  const p=document.createElement("p");p.textContent=copy;
  gate.append(h,p);control(gate,action,begin);
}
function reset(){
  x=24;y=planes.B.y;jumpY=0;velocity=0;stage=0;score=0;mode="ready";
  branch=null;branchTime=0;last=0;selected="";feedback="";collected.clear();
  byId("commands").replaceChildren();
  byId("hint").textContent="A sotto · B superficie · C sopra";
  overlay("Qwat World","Tre bivi, tre domande. Scegli i cartelli sul percorso.","Gioca");
  hud();paint();
}
function begin(){
  reset();
  byId("gate").hidden=true;
  mode="run";
  controls();
  canvas.focus();
  requestAnimationFrame(loop);
}
function controls(){
  const host=byId("commands");host.replaceChildren();
  if(mode==="choice"){
    const q=questions[stage];
    byId("hint").textContent=q.t+" · Scegli un cartello";
    Object.entries(q.o).forEach(([key,value])=>control(host,key+" "+value,()=>choose(key),planes[key].label+": "+key+" "+value));
    host.querySelector("button")?.focus();
  }else if(mode==="end"){
    byId("hint").textContent=score+" risposte corrette su 3";
  }else{
    byId("hint").textContent=feedback||"Spazio o ↑ per saltare e raccogliere monete";
    control(host,"Salta ↑",()=>{jump();canvas.focus();});
  }
}
function jump(){if(mode==="run"&&jumpY===0)velocity=280;}
function choose(key){
  if(mode!=="choice"||!Object.hasOwn(questions[stage].o,key))return;
  const q=questions[stage];
  selected=key;
  if(key===q.answer){score++;feedback="Risposta corretta";}
  else feedback="Risposta corretta: "+q.answer+" · "+q.o[q.answer];
  branch={from:y,to:planes[key].y};
  jumpY=velocity=0;branchTime=0;last=0;mode="branch";
  canvas.focus();controls();hud();requestAnimationFrame(loop);
}
function loop(now){
  if(!["run","branch"].includes(mode))return;
  const dt=last?Math.max(0,Math.min((now-last)/1000,.045)):0;last=now;
  if(mode==="branch"){
    branchTime+=dt;
    x+=140*dt;
    const progress=Math.min(1,branchTime/.70);
    y=branch.from+(branch.to-branch.from)*(reduced?1:progress);
    if(progress===1){stage++;mode="run";hud();}
  }else{
    x+=154*dt;
    if(dt>0&&(jumpY>0||velocity>0)){
      jumpY=Math.max(0,jumpY+velocity*dt);
      velocity=jumpY===0?0:velocity-740*dt;
    }
    if(jumpY>18){
      for(const token of tokenPositions)if(Math.abs(x-token)<16&&!collected.has(token)){collected.add(token);hud();}
    }
    if(stage<3&&x>=markers[stage]){
      x=markers[stage];mode="choice";last=0;controls();
    }else if(x>=finish){
      mode="end";controls();
      overlay("Traguardo",score+"/3 risposte corrette · "+collected.size+" monete","Rigioca");
    }
  }
  paint();
  if(["run","branch"].includes(mode))requestAnimationFrame(loop);
}
window.addEventListener("keydown",event=>{
  const key=event.key.toUpperCase();
  if(mode==="choice"&&Object.hasOwn(questions[stage].o,key)){event.preventDefault();choose(key);}
  if(mode==="run"&&["Space","ArrowUp"].includes(event.code)){event.preventDefault();jump();}
});
canvas.addEventListener("pointerup",event=>{
  if(mode==="run"){jump();return;}
  if(mode!=="choice")return;
  const bounds=canvas.getBoundingClientRect();
  const px=(event.clientX-bounds.left)*W/bounds.width;
  const py=(event.clientY-bounds.top)*H/bounds.height;
  if(px<307||px>448)return;
  const key=Object.keys(questions[stage].o).find(option=>Math.abs(py-(planes[option].y-31))<=25);
  if(key)choose(key);
});
function platform(y,height,base,top,cam){
  rect(base,0,y,W,height);rect(top,0,y,W,7);
  for(let i=-1;i<17;i++){
    const px=i*30-cam%30;
    rect("#221c2a66",px,y+9,24,4);
    rect("#fff1b025",px+10,y+16,13,4);
  }
}
function paint(){
  const cam=Math.max(0,x-70);
  rect("#5ac0db",0,0,W,239);
  rect("#35444a",0,239,W,H-239);
  for(let i=0;i<5;i++){
    const p=((135*i-cam*.15)%540+540)%540-42;
    rect("#e3f6ce",p,67+i%2*20,71,14);rect("#e3f6ce",p+11,57+i%2*20,38,13);
  }
  for(let i=0;i<9;i++){
    const p=((78*i-cam*.31)%540+540)%540-40;
    rect("#418976",p,170+i%3*14,80,58);rect("#63a884",p+14,159+i%3*14,42,16);
  }
  platform(131,22,"#807d40","#e4c761",cam);
  platform(239,26,"#8e5236","#a1c94b",cam);
  platform(347,83,"#53433a","#b89463",cam);
  label("3  SOPRA",11,115,12,"#143e38");
  label("2  SUPERFICIE",11,218,12,"#173627");
  label("1  SOTTO",11,326,12,"#fff3b5");
  const active=stage<3?questions[stage]:null;
  if(active){
    const anchor=markers[stage]-cam;
    if(anchor>-200&&anchor<W+120){
      const boardX=anchor-55;
      rect("#62412b",boardX+16,49,6,77);rect("#62412b",boardX+224,49,6,77);
      rect("#38251f",boardX,8,253,88);rect("#ffe199",boardX+4,12,245,80);
      label("DOMANDA "+(stage+1),boardX+13,30,12,"#8b3a28");
      wrap(active.t,boardX+13,51,226);
      for(const [key,value] of Object.entries(active.o)){
        const dest=planes[key].y, sx=anchor+239, sy=dest-51;
        if(mode==="choice"||mode==="branch"){
          path(anchor+16,(branch?.from??y)-6,sx-10,dest-6,"#fff0a1",5);
        }
        rect("#4d2c25",sx+46,sy+37,7,14);rect("#3b2723",sx,sy,112,40);
        rect(key===selected&&mode==="branch"?"#ffb64d":"#fff0af",sx+3,sy+3,106,34);
        label(key+"  "+value,sx+56,sy+26,22,undefined,"center");
      }
    }
  }
  tokenPositions.forEach(token=>{
    const p=token-cam;if(p<0||p>W||collected.has(token))return;
    rect("#995e23",p-7,y-53,13,17);rect("#ffd244",p-5,y-51,9,13);rect("#fff1ae",p-1,y-49,2,7);
  });
  if(finish-cam<W){
    const p=finish-cam;rect("#fff6d0",p,Math.max(0,y-86),5,86);
    rect("#e84b40",p+5,y-84,29,18);label("ARRIVO",p-24,y-94,12,"#231c23");
  }
  const px=x-cam,py=y-jumpY;
  rect("#332433",px-15,py-29,30,23);rect("#ed514a",px-13,py-27,26,15);
  rect("#f8d68e",px-7,py-16,17,10);rect("#402a3a",px+5,py-15,4,4);
  rect("#263c7a",px-10,py-6,21,6);rect("#39251f",px-13,py-3,10,4);
}
reset();
