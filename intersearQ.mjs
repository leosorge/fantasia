import { readFile, writeFile, rename } from "node:fs/promises";
import { parseArgs } from "node:util";
import { pathToFileURL } from "node:url";

export function parseTopics(text) {
  const topics = [];
  let group;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/^\uFEFF/,"").trim();
    if (!line || line.startsWith("#")) continue;
    const heading = line.match(/^\d+\.\s+(.+)$/);
    const entries = line.match(/^\d+\s+parol[ae]\s*:\s*(.+)$/i);
    if (heading) { group = {name:heading[1],terms:[]}; topics.push(group); }
    else if (entries && group) group.terms.push(...entries[1].split(",").map(term=>term.trim()).filter(Boolean));
    else throw new Error("Riga Qlist non riconosciuta: " + line);
  }
  if (!topics.length || topics.some(group=>!group.terms.length)) throw new Error("Qlist deve contenere almeno una categoria con termini.");
  return topics.map(group=>({...group,terms:[...new Set(group.terms)]}));
}

const contextual = new Set(["Willow","Helios","Nighthawk","Tempo","Cirq","Braket","cryptanalysis","drug discovery","portfolio optimization","materials simulation","industry pilot project","control electronics","hybrid workflow"]);
const quote = term => '"' + term.replace(/["|]/g,"") + '"';
export function planSearch(topics) {
  return topics.flatMap(({name,terms})=>{
    const batches = [];
    for (let offset=0;offset<terms.length;offset+=4) {
      const batch=terms.slice(offset,offset+4);
      batches.push({group:name,terms:batch,query:batch.map(term=>quote(term)+(contextual.has(term) ? " quantum" : "")).join("|")});
    }
    return batches;
  });
}

function normalize(text) {
  return text.toLowerCase().normalize("NFKC").replace(/[‐‑–—]/g,"-").replace(/\s+/g," ");
}
function termsInVideo(plan,item) {
  const snippet=item.snippet;
  const raw=normalize([snippet.title,snippet.description,...(snippet.tags ?? [])].join(" "));
  return plan.terms.filter(term=>{
    const escaped=normalize(term).replace(/[.*+?^{}()|[\]\\]/g,"\\$&");
    return new RegExp("(?<![\\p{L}\\p{N}])"+escaped+"(?![\\p{L}\\p{N}])","u").test(raw)
      && (!contextual.has(term) || /\bquantum\b|\bqubits?\b/.test(raw));
  });
}
export async function scan(topics,{request,days=1,channels=new Set(),limit=25,now=Date.now()}) {
  const plans=planSearch(topics);
  const candidates=new Map();
  const publishedAfter=new Date(now-days*86_400_000).toISOString();
  for (const plan of plans) {
    const payload=await request("search",{part:"snippet",q:plan.query,type:"video",videoDuration:"medium",order:"relevance",publishedAfter,maxResults:String(limit)});
    for (const item of payload.items ?? []) {
      const id=item.id?.videoId;
      if (!id) continue;
      if (!candidates.has(id)) candidates.set(id,[]);
      candidates.get(id).push(plan);
    }
  }
  const ids=[...candidates.keys()];
  const results=[];
  for (let offset=0;offset<ids.length;offset+=50) {
    const payload=await request("videos",{part:"snippet,contentDetails",id:ids.slice(offset,offset+50).join(",")});
    for (const item of payload.items ?? []) {
      const {snippet,id}=item;
      if (channels.size && !channels.has(snippet.channelId)) continue;
      const duration=item.contentDetails?.duration?.match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/);
      if (!duration) continue;
      const seconds=(+duration[1]||0)*3600+(+duration[2]||0)*60+(+duration[3]||0);
      if (seconds<240 || seconds>1200) continue;
      const tags=candidates.get(id).flatMap(plan=>termsInVideo(plan,item).map(term=>({category:plan.group,term})));
      if (!tags.length) continue;
      results.push({id,title:snippet.title,channel:snippet.channelTitle,channelId:snippet.channelId,published:snippet.publishedAt,seconds,tags,url:"https://www.youtube.com/watch?v="+id});
    }
  }
  return results.sort((a,b)=>b.published.localeCompare(a.published));
}

const escape = value => String(value).replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
export function report(results, metadata) {
  const items=results.map(video=>'<li><a href="'+escape(video.url)+'">'+escape(video.title)+'</a><div>'+escape(video.channel)+' · '+escape(video.published.slice(0,10))+' · '+Math.floor(video.seconds/60)+':'+String(video.seconds%60).padStart(2,"0")+'</div><small>'+escape(video.tags.map(tag=>tag.category+" / "+tag.term).join(" · "))+'</small></li>');
  return '<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>intersearQ</title><style>body{font:16px/1.5 system-ui;background:#10161c;color:#ecf6f6;max-width:840px;margin:32px auto;padding:0 20px}a{color:#a2f0d6}li{padding:10px 0}small{color:#bacbd0}</style><h1>intersearQ</h1><p>'+escape(metadata)+'</p>'+(items.length ? '<ol>'+items.join("")+'</ol>' : '<p>Nessun video corrispondente nella finestra selezionata.</p>')+'</html>';
}

async function main() {
  const {values}=parseArgs({options:{
    list:{type:"string"},days:{type:"string",default:"1"},limit:{type:"string",default:"25"},
    channels:{type:"string"},output:{type:"string",default:"intersearQ.html"},
    "dry-run":{type:"boolean"},json:{type:"boolean"}
  }});
  const days=Number(values.days), limit=Number(values.limit);
  if (!Number.isInteger(days) || days<1 || days>365 || !Number.isInteger(limit) || limit<1 || limit>50) throw new Error("Usa --days da 1 a 365 e --limit da 1 a 50.");
  const topics=parseTopics(await readFile(values.list ?? new URL("./Qlist.txt",import.meta.url),"utf8"));
  if (values["dry-run"]) {
    const plan=planSearch(topics);
    console.log(JSON.stringify({terms:topics.reduce((sum,group)=>sum+group.terms.length,0),queries:plan.length,plan},null,2));
    return;
  }
  const key=process.env.YOUTUBE_API_KEY?.trim();
  if (!key) throw new Error("Imposta YOUTUBE_API_KEY oppure usa --dry-run.");
  const channels=new Set(values.channels ? (await readFile(values.channels,"utf8")).replace(/^\uFEFF/,"").split(/\r?\n/).map(line=>line.trim()).filter(line=>line && !line.startsWith("#")) : []);
  if (values.channels && (!channels.size || [...channels].some(id=>!/^UC[\w-]{22}$/.test(id)))) throw new Error("Il file dei canali deve contenere ID YouTube validi, uno per riga.");
  const request=async (route,params)=>{
    const url=new URL("https://www.googleapis.com/youtube/v3/"+route);
    url.search=new URLSearchParams(params);
    let response;
    try { response=await fetch(url,{headers:{"x-goog-api-key":key},signal:AbortSignal.timeout(20_000)}); }
    catch { throw new Error("Connessione a YouTube non riuscita durante "+route+"."); }
    if (!response.ok) {
      const payload=await response.json().catch(()=>({}));
      const reason=payload.error?.errors?.[0]?.reason;
      throw new Error("YouTube "+route+" HTTP "+response.status+(reason ? " · "+reason : ""));
    }
    return response.json();
  };
  const results=await scan(topics,{request,days,limit,channels});
  const metadata=results.length+" video · ultimi "+days+" giorni · "+(channels.size ? channels.size+" canali selezionati" : "tutti i canali");
  const temp=values.output+"."+process.pid+".tmp";
  await writeFile(temp,values.json ? JSON.stringify(results) : report(results,metadata),"utf8");
  await rename(temp,values.output);
  console.log(metadata+" → "+values.output);
}
if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  main().catch(error=>{console.error(error.message);process.exitCode=1;});
}
