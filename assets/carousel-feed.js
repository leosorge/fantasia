const config=JSON.parse(document.getElementById("slides").textContent);
const get=id=>document.getElementById(id);
const deck=get("deck");
let index=0;
function render(){
  const system=get("visualStyle").value;
  const cover=index===0;
  const photo=cover&&config.photo;
  const sheet=system==="corporate-modular"&&!photo;
  const dark=!sheet&&(cover||index%2===0);
  const color=config.palette;
  const slide=config.slides[index];
  deck.className="slide-preview visual-system-"+system+(photo?" has-cover-image cover-split":cover?" typographic-cover":"");
  deck.dataset.kind=cover?"cover":"item";
  deck.dataset.surface=dark?"dark":"light";
  deck.dataset.constellationPosition=index%2?"low":"high";
  deck.style.setProperty("--preview-bg",dark?color.background_dark:color.background_light);
  deck.style.setProperty("--preview-text",dark?color.text_on_dark:color.text_on_light);
  get("art").hidden=!photo;
  get("constellation").hidden=Boolean(photo);
  get("frameField").hidden=Boolean(photo);
  const title=get("slideTitle");
  title.textContent=slide.title;title.hidden=!slide.title;
  const body=get("slide");
  body.hidden=!slide.text;
  body.replaceChildren();
  if(config.verbatim)body.textContent=slide.text;
  else slide.text.split("\n").filter(Boolean).forEach(sentence=>{
    const line=document.createElement("span");
    line.className="preview-sentence";line.textContent=sentence;body.append(line);
  });
  get("page").textContent=String(index+1).padStart(2,"0")+" / "+String(config.slides.length).padStart(2,"0");
  get("back").disabled=index===0;
  get("next").disabled=index===config.slides.length-1;
}
get("back").onclick=()=>{if(index>0){index--;render();}};
get("next").onclick=()=>{if(index<config.slides.length-1){index++;render();}};
get("visualStyle").onchange=render;
get("carousel").addEventListener("keydown",event=>{
  if(event.target===get("visualStyle"))return;
  if(event.key==="ArrowLeft")get("back").click();
  if(event.key==="ArrowRight")get("next").click();
});
render();
