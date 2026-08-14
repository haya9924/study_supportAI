/* 共有 SRS ストア (localStorage 永続化・FSRS 風の簡易スケジューリング)
 *
 * 形式:  window.SRS = { [nodeId]: [ {due, interval, ease, reps}, ... ] }
 *   - due: 残り日数 (0 = 今日/期限超過, 1 = 明日, ...)
 *   - カードの内容 (表/裏) は各ページが持つ問題データから `SRS.dueIdx()` の
 *     インデックスで参照する (内容はストアに持たない)。
 */
(function(){
  var KEY='srsCards';
  var store=null;
  function load(){
    try{ return JSON.parse(localStorage.getItem(KEY)||'null')||{}; }catch(e){ return {}; }
  }
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(store)); }catch(e){} }

  window.SRS={
    _store:function(){ if(store===null) store=load(); return store; },

    /* 未作成なら total 枚を生成。最初の dueToday 枚は今日(0)、残りは日毎に分散。 */
    ensure:function(id,total,dueToday){
      var st=this._store();
      if(st[id]&&st[id].length) return;
      var dt=(dueToday==null)?Math.min(3,total):dueToday;
      var arr=[];
      for(var i=0;i<total;i++){
        var due=(i<dt)?0:Math.max(1,i-dt+1);
        arr.push({due:due,interval:1,ease:2.5,reps:0});
      }
      st[id]=arr; save();
    },

    /* 今日復習すべきカード数 */
    dueCount:function(id){
      var st=this._store();
      if(!st[id]) return 0;
      return st[id].filter(function(c){ return c.due<=0; }).length;
    },

    /* 今日復習すべきカードのインデックス配列 */
    dueIdx:function(id){
      var st=this._store();
      if(!st[id]) return [];
      var out=[];
      st[id].forEach(function(c,i){ if(c.due<=0) out.push(i); });
      return out;
    },

    /* 全カード (次回予定の表示用) */
    all:function(id){
      var st=this._store();
      return st[id]||[];
    },

    /* ○/× でカードを更新 (FSRS 風: 間隔と易しさを調整) */
    mark:function(id,idx,correct){
      var st=this._store();
      if(!st[id]||!st[id][idx]) return;
      var s=st[id][idx];
      if(correct){
        s.reps++;
        s.interval=s.reps===1?1:Math.max(1,Math.round(s.interval*s.ease));
        s.ease=Math.min(3,+(s.ease+0.05).toFixed(2));
        s.due=s.interval;
      }else{
        s.reps=0;
        s.interval=1;
        s.ease=Math.max(1.7,+(s.ease-0.2).toFixed(2));
        s.due=0; /* 再び今日 */
      }
      save();
    }
  };
})();