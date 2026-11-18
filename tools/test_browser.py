import json
from playwright.sync_api import sync_playwright
URL='file:///home/claude/mushaf-app/app/src/main/assets/www/index.html'
B=json.load(open('/tmp/bridge.json',encoding='utf-8'))
MOCK="""const BR=%s;const ST=JSON.parse(sessionStorage.getItem('st')||'{}');window.__c={screen:[],full:[],urls:[]};
window.Android={getRiwayat:()=>JSON.stringify(BR.riwayat),getMeta:r=>BR.rw[r].meta,getPage:(r,p)=>BR.rw[r].pages[p-1],getAbout:()=>JSON.stringify(BR.about),
 openUrl:u=>__c.urls.push(u),setFullscreen:o=>__c.full.push(o),
 findPage:(r,s,a)=>{let m=BR.vp[r];for(let x=a;x>=1;x--){if(m[s+'_'+x])return m[s+'_'+x]}return 0},
 getSetting:k=>ST[k]===undefined?'':ST[k],setSetting:(k,v)=>{ST[k]=v;sessionStorage.setItem('st',JSON.stringify(ST))},keepScreenOn:o=>__c.screen.push(o)};"""%json.dumps(B,ensure_ascii=False)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':400,'height':800}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.add_init_script(MOCK); pg.goto(URL); pg.wait_for_timeout(500)
    ev=pg.evaluate
    pg.click('#v'); pg.wait_for_timeout(300)
    # zoom dropdown: zoom controls + full screen under it
    pg.click('#zm'); pg.wait_for_timeout(250)
    print('zoom panel  :',ev("[...document.querySelectorAll('#zr button')].map(b=>b.textContent)"))
    pg.screenshot(path='/tmp/t1_zoom.png')
    pg.click('#zr .fsb'); print('fullscreen  :',ev("__c.full"),'| label:',ev("document.querySelector('#zr .fsb').textContent"))
    # menu home grid
    pg.click('#mi'); pg.wait_for_timeout(250)
    print('grid        :',ev("getComputedStyle(gd).gridTemplateColumns.split(' ').length"),'cols x',ev("gd.children.length/5"),'rows | tiles:',ev("[...gd.children].map(b=>b.textContent)"))
    print('menu opaque :',ev("getComputedStyle(ix).backgroundColor"))
    pg.screenshot(path='/tmp/t2_grid.png')
    pg.click('#gd [data-a="f+"]'); print('A+ tile     :',ev("fs3=0,document.getElementById('gst').textContent"))
    pg.click('#gd [data-a="thumn"]'); print('thumn list  :',ev("ls.children.length"),'| title:',ev("st2.textContent"))
    pg.click('#bk'); print('back -> grid:',ev("getComputedStyle(hm).display"))
    pg.click('#gd [data-a="ab"]'); pg.wait_for_timeout(200)
    print('about cards :',ev("document.querySelectorAll('#ab .ac').length"),'| links:',ev("document.querySelectorAll('#ab .lk').length"))
    pg.screenshot(path='/tmp/t3_about.png')
    pg.click('#ab .lk'); print('open url    :',ev("__c.urls"))
    pg.click('#bk'); pg.click('#gd [data-a="rw"]'); pg.click('#ls [data-rw="warsh"]'); pg.wait_for_timeout(900)
    pg.click('#v'); pg.wait_for_timeout(300); pg.click('#mi'); pg.wait_for_timeout(200)
    print('warsh grid  :',ev("[...gd.querySelectorAll('.tl.off')].map(b=>b.textContent)"))
    pg.click('#gd [data-a="juz"]'); print('off tile tap:',ev("tt.textContent"),'| still on grid:',ev("getComputedStyle(hm).display"))
    pg.click('#x')
    # tap during auto scroll must not show the bar
    pg.click('#play'); pg.wait_for_timeout(500); print('playing     :',ev("document.getElementById('play').textContent"),'| bar shown:',ev("bar.classList.contains('s')"))
    pg.mouse.click(200,400); pg.wait_for_timeout(300)
    print('tap while playing -> stopped:',ev("document.getElementById('play').textContent==='▶'"),'| bar shown:',ev("bar.classList.contains('s')"))
    pg.mouse.click(200,400); pg.wait_for_timeout(300); print('second tap  : bar shown:',ev("bar.classList.contains('s')"))
    print('font default for warsh:',ev("document.getElementById('fn').value"),'| errors:',errs); b.close()
