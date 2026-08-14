/* 共有のマップ定数・ノードデータ (home.html / stats.html で利用)
 *
 * 状態 (state) は各ページが localStorage から読み込んで上書きするため、
 * ここでは初期値だけを持つ。createNodes() は毎回新しい配列を返す。
 */
const W=2400,H=1760,RX=52,PERSP=3000,YAW=-16;
const cg=Math.cos(YAW*Math.PI/180), sg=Math.sin(YAW*Math.PI/180);
const THICK=60,BOSS_THICK=84,GATE_THICK=40;
function TH(n){return n.type==='boss'?BOSS_THICK:(n.type==='gate'?GATE_THICK:THICK);}

const ZONES = [
  {name:'プラン',x:60,y:40,w:2280,h:900,locked:false},
  {name:'光合成',x:60,y:960,w:1520,h:780,locked:false},
  {name:'細胞分裂（未解放）',x:1620,y:960,w:740,h:780,locked:true},
];

const STATE_LABEL = {green:'できる',yellow:'怪しい',red:'わからない',in_progress:'進行中',unlocked:'未着手',locked:'ロック'};
const TYPE_LABEL = {plan:'プラン',discovery:'発見',basic:'基礎',practice:'演習',merge:'合流',boss:'ボス',branch:'補強',gate:'診断ゲート',application:'応用'};
const TYPE_DESC = {
  plan:'教材で科目を追加すると作成される、科目ごとのプランノードです。AIが教材から学習マップを組み立てます。',
  discovery:'教材を読んで概要をつかむ（インプットは最小限）。Day1 の入口。',
  basic:'単一概念の理解を確認する。短答・選択で答える。',
  practice:'反復練習で「できる」化する。量ベースで進める。',
  merge:'複数の要素を組み合わせる総合問題。前提ノードが全て必要。',
  boss:'章の総仕上げ。テスト形式・時間制限あり。診断ゲートを通過後に挑戦。',
  branch:'失敗を補強する代替ルート。要素分解・別アプローチ・暗記特化。',
  gate:'前提ノードから混合問題を自動生成し、弱点を検出する診断ゲート。弱点があれば該当ノードを黄へ降格し、補強ブランチを提示します。',
  application:'ボスクリア後に挑戦できる発展ステージ。他分野との連携・応用問題。',
};
let TEST_DAYS=14;

function createNodes(){
  return [
    /* ---- Zone A 光合成 ---- */
    {id:'d1',zone:'A',type:'discovery',name:'光合成とは',x:200,z:1320,w:180,h:64,state:'green',stars:3},
    {id:'b1',zone:'A',type:'basic',name:'葉緑体の構造',x:420,z:1030,w:170,h:64,state:'green',stars:2,from:['d1']},
    {id:'b2',zone:'A',type:'basic',name:'光エネルギーとATP',x:420,z:1320,w:190,h:64,state:'green',stars:3,from:['d1']},
    {id:'b3',zone:'A',type:'basic',name:'水の分解と酸素',x:420,z:1560,w:180,h:64,state:'yellow',stars:1,from:['d1']},
    {id:'g1',zone:'A',type:'gate',name:'基礎チェック',x:650,z:1320,w:140,h:52,state:'green',stars:0,from:['b1','b2','b3']},
    {id:'b4',zone:'A',type:'practice',name:'CO₂の固定 演習',x:650,z:1030,w:170,h:64,state:'unlocked',stars:0,from:['b1']},
    {id:'br1',zone:'A',type:'branch',name:'水の分解ミニ（補強）',x:650,z:1670,w:190,h:58,state:'red',stars:0,from:['b3']},
    {id:'m1',zone:'A',type:'merge',name:'明反応の全体像',x:930,z:1320,w:190,h:68,state:'in_progress',stars:0,day:2,from:['g1','br1'],today:true},
    {id:'m2',zone:'A',type:'merge',name:'暗反応（カルビン回路）',x:1130,z:1320,w:200,h:68,state:'locked',stars:0,from:['b4','m1']},
    {id:'g2',zone:'A',type:'gate',name:'ボス前チェック',x:1340,z:1320,w:140,h:52,state:'locked',stars:0,from:['m2']},
    {id:'bossA',zone:'A',type:'boss',name:'光合成マスター',x:1340,z:1560,w:200,h:72,state:'locked',stars:0,from:['g2']},
    {id:'appA',zone:'A',type:'application',name:'光合成と生活（応用）',x:1340,z:1670,w:170,h:56,state:'locked',stars:0,from:['bossA']},
    /* ---- Zone B 細胞分裂（ロック） ---- */
    {id:'d2',zone:'B',type:'discovery',name:'細胞分裂とは',x:1640,z:1320,w:160,h:64,state:'locked'},
    {id:'b5',zone:'B',type:'basic',name:'体細胞分裂',x:1640,z:1060,w:160,h:64,state:'locked',from:['d2']},
    {id:'b6',zone:'B',type:'basic',name:'減数分裂',x:1640,z:1580,w:160,h:64,state:'locked',from:['d2']},
    {id:'g3',zone:'B',type:'gate',name:'合流前チェック',x:1830,z:1320,w:140,h:52,state:'locked',from:['b5','b6']},
    {id:'m3',zone:'B',type:'merge',name:'細胞周期の流れ',x:2000,z:1320,w:170,h:68,state:'locked',from:['g3']},
    {id:'g4',zone:'B',type:'gate',name:'ボス前チェック',x:2000,z:1060,w:140,h:52,state:'locked',from:['m3']},
    {id:'bossB',zone:'B',type:'boss',name:'細胞分裂マスター',x:2180,z:1320,w:180,h:72,state:'locked',from:['g4']},
  ];
}