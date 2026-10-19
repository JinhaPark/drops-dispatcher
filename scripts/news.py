import json,os,urllib.request,urllib.parse,xml.etree.ElementTree as ET,datetime,html,re,pathlib
P=pathlib.Path('data');P.mkdir(exist_ok=True)
def load(p,default):
 try:return json.loads(pathlib.Path(p).read_text())
 except FileNotFoundError:return default
def save(p,obj):pathlib.Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def request(url,method='GET',payload=None):
 data=json.dumps(payload).encode() if payload is not None else None
 req=urllib.request.Request(url,data=data,method=method,headers={'User-Agent':'AIEngineeringNews/1.0','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=25) as r:return r.read().decode()
def strip(s):return re.sub('<[^>]+>',' ',html.unescape(s or '')).strip()
def fetch():
 sources=load('sources.json',[]);seen=set(load(P/'seen.json',[]));pending=load(P/'pending.json',[]);known={x['id'] for x in pending};found=[]
 for source in sources:
  if not source.get('enabled') or not source.get('feed_url'):
   print('No verified feed configured:',source['id']);continue
  try:
   root=ET.fromstring(request(source['feed_url']))
   for entry in root.findall('.//item')[:20]:
    title=entry.findtext('title') or '';link=entry.findtext('link') or '';guid=entry.findtext('guid') or link
    uid=source['id']+':'+guid
    if not link or uid in seen or uid in known:continue
    date=entry.findtext('pubDate') or ''
    try:date=datetime.datetime.strptime(date[:25],'%a, %d %b %Y %H:%M:%S').date().isoformat()
    except ValueError:date=datetime.date.today().isoformat()
    found.append({'id':uid,'source':source['id'],'date':date,'title':strip(title),'author':source.get('author'),'url':link,'excerpt':strip(entry.findtext('description'))[:1000],'status':'needs_editorial_review'})
  except Exception as e:print('Source unavailable:',source['id'],type(e).__name__,str(e)[:150])
 pending+=found;save(P/'pending.json',pending);print('New drafts:',len(found))
def build():
 articles=load(P/'articles.json',[]);sources={s['id']:s for s in load('sources.json',[])};ids=set()
 for a in articles:
  if a['id'] in ids:raise ValueError('Duplicate article '+a['id'])
  ids.add(a['id']);s=sources[a['source']];n=len(a['summary'])
  if not 180<=len(a['summary'].split())<=430:raise ValueError('Summary must be approximately 300 Korean words: '+a['id'])
  for section in s.get('sections',[]):
   if section.get('required') and section['type']=='project_roundup' and not a.get('roundup_verified'):raise ValueError('Unverified roundup: '+a['id'])
 articles.sort(key=lambda a:a['date'],reverse=True);out=pathlib.Path('dist');out.mkdir(exist_ok=True)
 esc=html.escape;cards=[]
 for a in articles:
  projects=''.join('<li><a href="'+esc(p['url'],quote=True)+'">'+esc(p['name'])+'</a> — '+esc(p['description'])+'</li>' for p in a.get('projects',[]))
  cards.append('<article id="'+esc(urllib.parse.quote(a['id']),quote=True)+'"><small>'+esc(a['date'])+' · '+esc(sources[a['source']]['name'])+'</small><h2><a href="'+esc(a['url'],quote=True)+'">'+esc(a['title'])+'</a></h2><p>'+esc(a['summary'])+'</p>'+('<h3>주간 프로젝트</h3><ul>'+projects+'</ul>' if projects else '')+'</article>')
 style='body{font-family:system-ui,-apple-system,sans-serif;max-width:740px;margin:auto;padding:24px 16px;background:#f7f9fc;color:#192234;line-height:1.8}a{color:#165db5}article{background:white;border:1px solid #e0e5ed;border-radius:16px;padding:22px;margin:18px 0;overflow-wrap:anywhere}small{color:#64748b}h2{font-size:1.25rem;line-height:1.5}li{margin:8px 0}@media(prefers-color-scheme:dark){body{background:#0e1522;color:#e2e8f0}article{background:#192337;border-color:#344256}a{color:#93c5fd}}'
 (out/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Engineering News</title><style>'+style+'</style><header><h1>AI Engineering News</h1><p>Artificial Engineering · Elevate — 한국어 기술 브리핑</p><a href="feed.xml">RSS</a></header><main>'+(''.join(cards) if cards else '<article>검증된 요약을 준비 중입니다.</article>')+'</main></html>')
 base='https://jinhapark.github.io/news/'
 items=''.join('<item><title>'+esc(a['title'])+'</title><link>'+esc(base+'#'+urllib.parse.quote(a['id']))+'</link><guid isPermaLink="false">'+esc(a['id'])+'</guid><description>'+esc(a['summary'])+'</description></item>' for a in articles)
 (out/'feed.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>AI Engineering News</title><link>'+base+'</link><description>Korean AI engineering digest</description>'+items+'</channel></rss>')
def notify():
 url=os.environ.get('DISCORD_WEBHOOK_URL');published=load(P/'articles.json',[]);notified=set(load(P/'notified.json',[]));new=[a for a in published if a['id'] not in notified]
 if not url:print('Discord secret absent; skipping');return
 for a in sorted(new,key=lambda a:a['date']):
  msg={'content':a['date']+' | **'+a['title'][:150]+'**\\n'+a['url']+'\n'+a['summary'][:800]}
  try:request(url,method='POST',payload=msg)
  except Exception as e:print('Discord failed:',type(e).__name__);break
  notified.add(a['id']);save(P/'notified.json',sorted(notified))
if __name__=='__main__':
 import sys
 {'fetch':fetch,'build':build,'notify':notify}[sys.argv[1]]()
