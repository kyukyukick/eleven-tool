import streamlit as st
import random

# --- クラス・関数定義 ---

class Player:
    def __init__(self, strength, role):
        self.strength = strength
        self.role = role # 'att' or 'def'
    def __repr__(self):
        icon = "⚽" if self.role == 'att' else "🛡️"
        return f"{icon}{self.strength}"

def parse_input(text):
    """入力文字列(例: 'A2 D1')を解析"""
    players = []
    if not text: return players
    text = text.replace("　", " ").upper()
    tokens = text.split()
    for t in tokens:
        try:
            role_char = t[0]
            strength = int(t[1:])
            if role_char == 'A': players.append(Player(strength, 'att'))
            elif role_char == 'D': players.append(Player(strength, 'def'))
        except: pass
    return players

def resolve_clash(attackers, defenders, side_name, is_variant):
    """
    攻撃解決ロジック
    """
    successful_shots = []
    available_defenders = sorted(defenders, key=lambda x: x.strength)
    sorted_attackers = sorted(attackers, key=lambda x: x.strength, reverse=True)
    
    log = []
    
    for att in sorted_attackers:
        candidate_indices = [i for i, d in enumerate(available_defenders) if d.strength >= att.strength]
        
        if candidate_indices:
            idx = candidate_indices[0]
            blocker = available_defenders.pop(idx)
            log.append(f"❌ {side_name}攻撃(強度{att.strength}) vs DF(強度{blocker.strength}) -> ブロック成功")
        else:
            successful_shots.append(att.strength)
            if available_defenders:
                if is_variant:
                    sacrificed = available_defenders.pop() 
                    log.append(f"⚠️ {side_name}シュート(強度{att.strength}) -> DF(強度{sacrificed.strength})は止められず無駄消費 (Variant)")
                else:
                    sacrificed = available_defenders.pop(0)
                    log.append(f"⚠️ {side_name}シュート(強度{att.strength}) -> DF(強度{sacrificed.strength})突破 (Base)")
            else:
                log.append(f"⚠️ {side_name}シュート(強度{att.strength}) -> フリー (DF不在)")
                
    return successful_shots, available_defenders, log

def try_save(shots, main_gk_gloves, main_gk_str, bonus_gloves, gk_name, attacking_team_name):
    """GKセーブ処理"""
    goals = 0
    remaining_bonus = bonus_gloves.copy()
    current_main_gloves = main_gk_gloves
    save_log = []
    
    for shot_str in shots:
        saved = False
        
        # 1. ボーナスグローブ
        bonus_candidates = [i for i, g in enumerate(remaining_bonus) if g >= shot_str]
        if bonus_candidates:
            bonus_idx = sorted(bonus_candidates)[0]
            val = remaining_bonus.pop(bonus_idx)
            saved = True
            save_log.append(f"🧤 {gk_name}: 余ったDF(強度{val})がカバーに入りセーブ！")
            
        # 2. メインGK
        if not saved and current_main_gloves > 0:
            if main_gk_str >= shot_str:
                current_main_gloves -= 1
                saved = True
                save_log.append(f"🙌 {gk_name}: 本人がセーブ (残グローブ{current_main_gloves})")
            else:
                save_log.append(f"🥅 {gk_name}: 強度不足({main_gk_str} < {shot_str})")
        
        if not saved:
            goals += 1
            save_log.append(f"⚽ {attacking_team_name} GOAL! (強度{shot_str})")
            
    return goals, current_main_gloves, remaining_bonus, save_log

# --- UI構築 ---

st.set_page_config(page_title="Eleven Match Solver", layout="wide")
st.title("⚽ Eleven Match Solver")

# チーム名入力
col_team1, col_team2 = st.columns(2)
with col_team1:
    my_team_name = st.text_input("自分のチーム名", value="My Team")
with col_team2:
    opp_team_name = st.text_input("相手のチーム名", value="Opponent")

# 設定エリア
st.markdown("---")
is_variant = st.checkbox('Anti-Moneyball Variant を有効にする', value=True)
if is_variant:
    st.info("設定ON: 最強DF犠牲ルール、余りDFのグローブ化、ダイス順序決定が適用されます。")
else:
    st.warning("設定OFF: 基本ルール（固定順、最弱DF消費、余りDF効果なし）で処理します。")

# GK入力
st.markdown("---")
st.subheader("🧤 ゴールキーパー設定")
col_gk1, col_gk2 = st.columns(2)

with col_gk1:
    st.markdown(f"**🔵 {my_team_name} GK**")
    my_gk_gloves = st.number_input("自分のグローブ数", 0, 10, 2)
    my_gk_str = st.number_input("自分のGK強度", 0, 10, 1)

with col_gk2:
    st.markdown(f"**🔴 {opp_team_name} GK**")
    opp_gk_gloves = st.number_input("相手のグローブ数", 0, 10, 1)
    opp_gk_str = st.number_input("相手のGK強度", 0, 10, 2)

# ゾーン入力
st.markdown("---")
st.subheader("📍 ゾーン配置")
st.caption("入力例: `A2 D1` (攻撃2, 守備1)")

zones_def = [
    ("Left Wing (左翼)", "LW"),
    ("Right Wing (右翼)", "RW"),
    ("Center Fwd (中央FW)", "CF"),
    ("Center Mid (中央MF)", "CM"),
    ("Center Def (中央DF)", "CD")
]

zone_inputs = {}

for z_label, z_id in zones_def:
    opp_label = ""
    if z_id == "LW": opp_label = "(vs 相手RW)"
    elif z_id == "RW": opp_label = "(vs 相手LW)"
    elif z_id == "CF": opp_label = "(vs 相手CD)"
    elif z_id == "CM": opp_label = "(vs 相手CM)"
    elif z_id == "CD": opp_label = "(vs 相手CF)"
    
    with st.expander(f"{z_label} {opp_label}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            w_my = st.text_input(f"{my_team_name} ({z_id})", key=f"my_{z_id}", placeholder='例: A2 D1')
        with c2:
            w_opp = st.text_input(f"{opp_team_name}", key=f"opp_{z_id}", placeholder='例: D2 A1')
        zone_inputs[z_id] = {'my': w_my, 'opp': w_opp, 'label': z_label}

# 実行ボタン
st.markdown("---")
if st.button("試合解決 (Resolve Match)", type="primary"):
    st.divider()
    
    # データ準備
    my_formation = {zid: parse_input(zone_inputs[zid]['my']) for _, zid in zones_def}
    opp_formation = {zid: parse_input(zone_inputs[zid]['opp']) for _, zid in zones_def}
    
    st.write(f"### ■ {my_team_name} vs {opp_team_name}")
    
    # 順序決定
    order_list = ["LW", "RW", "CF", "CM", "CD"]
    if is_variant:
        dice = random.randint(1, 6)
        order_type = "奇数: 左から (LW First)" if dice % 2 != 0 else "偶数: 右から (RW First)"
        st.success(f"🎲 ダイスロール: **{dice}** -> **{order_type}**")
        if dice % 2 == 0:
            order_list = ["RW", "LW", "CF", "CM", "CD"]
    else:
        st.info(f"📋 解決順序: 固定 (LW -> RW -> CF -> CM -> CD)")

    clash_map = {"LW": "RW", "RW": "LW", "CF": "CD", "CM": "CM", "CD": "CF"}

    user_score = 0
    opp_score = 0
    user_bonus = []
    opp_bonus = []
    
    # GK変数はループ内で変動するためコピー
    u_gk_g = my_gk_gloves
    o_gk_g = opp_gk_gloves

    for my_zid in order_list:
        opp_zid = clash_map[my_zid]
        z_label = zone_inputs[my_zid]['label']
        u_players = my_formation[my_zid]
        o_players = opp_formation[opp_zid]
        
        st.markdown(f"#### 📍 {z_label}")
        st.caption(f"{my_team_name}: {u_players}  vs  {opp_team_name}: {o_players}")
        
        u_att = [p for p in u_players if p.role == 'att']
        u_def = [p for p in u_players if p.role == 'def']
        o_att = [p for p in o_players if p.role == 'att']
        o_def = [p for p in o_players if p.role == 'def']

        # A. 自分攻撃
        shots, unused_o, log = resolve_clash(u_att, o_def, my_team_name, is_variant)
        for l in log: st.text(l)
        if is_variant:
            for d in unused_o: opp_bonus.append(d.strength)
            if unused_o and not shots: st.caption(f"🛡️ {opp_team_name}DF余り(強度{[d.strength for d in unused_o]}) -> 次のカバーへ")
        
        if shots:
            g, new_gk, new_bonus, s_log = try_save(shots, o_gk_g, opp_gk_str, opp_bonus, f"🔴{opp_team_name}GK", my_team_name)
            user_score += g
            o_gk_g = new_gk
            opp_bonus = new_bonus
            for l in s_log: st.text(l)

        # B. 相手攻撃
        st.write("---")
        shots, unused_u, log = resolve_clash(o_att, u_def, opp_team_name, is_variant)
        for l in log: st.text(l)
        if is_variant:
            for d in unused_u: user_bonus.append(d.strength)
            if unused_u and not shots: st.caption(f"🛡️ {my_team_name}DF余り(強度{[d.strength for d in unused_u]}) -> 次のカバーへ")

        if shots:
            g, new_gk, new_bonus, s_log = try_save(shots, u_gk_g, my_gk_str, user_bonus, f"🔵{my_team_name}GK", opp_team_name)
            opp_score += g
            u_gk_g = new_gk
            user_bonus = new_bonus
            for l in s_log: st.text(l)
        
        st.divider()

    # 結果表示
    st.header(f"🏆 結果: {user_score} - {opp_score}")
    if user_score > opp_score: st.success(f"🎉 {my_team_name} の勝利！")
    elif user_score < opp_score: st.error(f"💀 {my_team_name} の敗北...")
    else: st.warning("🤝 引き分け")
