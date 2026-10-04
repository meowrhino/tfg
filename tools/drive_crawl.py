import re,urllib.request,html,json,sys
seen=set();out=[]
def get(u): return urllib.request.urlopen(u).read().decode()
def crawl(fid,path):
    if fid in seen: return
    seen.add(fid)
    s=get(f'https://drive.google.com/embeddedfolderview?id={fid}')
    for href,title in re.findall(r'<div class="flip-entry".*?<a href="([^"]+)".*?<div class="flip-entry-title">(.*?)</div>',s,re.S):
        title=html.unescape(title); href=html.unescape(href)
        m=re.search(r'/folders/([\w-]+)',href)
        if m: crawl(m.group(1),path+'/'+title)
        else:
            out.append((path+'/'+title,href)); print(path+'/'+title,'|',href)
crawl(sys.argv[1],'')
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=0)
