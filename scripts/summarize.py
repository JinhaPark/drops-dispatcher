"""Generate Korean editorial drafts with immutable provenance and content-addressed cache."""
import os,json,hashlib,pathlib,urllib.request,datetime,re
ROOT=pathlib.Path("data"); ROOT.mkdir(exist_ok=True)
def read(p,default):
 try:return json.loads(pathlib.Path(p).read_text())
 except FileNotFoundError:return default
def write(p,obj):pathlib.Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def complete(text):return 180<=len(text.split())<=430 and text.rstrip().endswith(("습니다.","입니다.","까요.","니다."))
def generate(item,source):
 api=os.getenv("OPENAI_API_KEY")
 if not api:raise RuntimeError("OPENAI_API_KEY secret required")
 content=item.get("excerpt","").strip()
 if len(content)<300:raise ValueError("Insufficient source text; do not invent missing content")
 policy=source.get("sections",[])
 if any(s.get("required") for s in policy):
  raise ValueError("Required roundup cannot be verified from a feed excerpt; awaiting full-text extraction and editorial verification")
 model=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
 instructions=("한국에서 교육받은 고학력 성인 독자를 위한 기술 논픽션 편집자입니다. "
 "한국어 존댓말(합니다·입니다체)을 쓰고 번역투, 추상명사 나열, 불필요한 피동문을 피하세요. "
 "누가 무엇을 하는지 명확히 하고 문단과 문장을 자연스럽게 연결하세요. "
 "낯선 기술 용어는 짧게 설명하되 전문성을 낮추지 마세요. "
 "검증된 사실과 저자 주장을 구분하고 출처에 없는 내용은 만들지 마세요. "
 "본문은 한국어 어절 기준 약 300단어(권장 250~350어절)로 쓰세요. "
 "제목, 발행일, URL, 작성자는 입력 메타데이터 그대로 보존하며 JSON의 summary 필드만 생성하세요.")
 payload={"model":model,"instructions":instructions,"input":"원문에서 확인된 내용만 사용하세요:\n"+json.dumps({"title":item["title"],"author":item.get("author"),"published_at":item["date"],"source_url":item["url"],"source_text":content},ensure_ascii=False),"text":{"format":{"type":"json_schema","name":"summary","strict":True,"schema":{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"],"additionalProperties":False}}}}
 req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+api,"Content-Type":"application/json"},method="POST")
 with urllib.request.urlopen(req,timeout=120) as r:result=json.load(r)
 parts=[p.get("text","") for o in result.get("output",[]) for p in o.get("content",[]) if p.get("type")=="output_text"]
 if not parts:raise ValueError("No model output")
 summary=json.loads("".join(parts))["summary"].strip()
 if not complete(summary):raise ValueError("Generated summary failed word-count or style validation")
 return summary
def main():
 sources={s["id"]:s for s in read("sources.json",[])}
 pending=read(ROOT/"pending.json",[]);articles=read(ROOT/"articles.json",[])
 existing={a["id"] for a in articles};cache=read(ROOT/"summary-cache.json",{})
 for item in pending:
  if item["id"] in existing:continue
  source=sources[item["source"]]
  canonical=item["url"].split("#")[0]
  author=item.get("author") or source.get("author")
  if not author:print("Missing author:",item["id"]);continue
  if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",item["date"]):continue
  identity=sha(json.dumps([item["source"],canonical,author,item["date"]],ensure_ascii=False))
  source_hash=sha(item.get("excerpt",""))
  key=sha(json.dumps([identity,source_hash,os.getenv("OPENAI_MODEL","gpt-4.1-mini"),"ko-300w-v1"]))
  try:
   summary=cache.get(key,{}).get("summary") or generate(item,source)
   cache[key]={"identity":identity,"source_url":canonical,"author":author,"published_at":item["date"],"source_sha256":source_hash,"summary":summary,"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
   write(ROOT/"summary-cache.json",cache)
   articles.append({"id":item["id"],"source":item["source"],"date":item["date"],"author":author,"url":canonical,"title":item["title"],"summary":summary,"source_sha256":source_hash,"cache_key":key,"projects":[]})
   existing.add(item["id"])
  except Exception as e:print("Pending editorial review:",item["id"],str(e)[:160])
 write(ROOT/"articles.json",articles)
if __name__=="__main__":main()
