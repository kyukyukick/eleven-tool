import streamlit as st
import random

# --- クラス定義 ---
class Player:
    def __init__(self, strength, role):
        self.strength = strength
        self.role = role  # 'att' or 'def'
    def __repr__(self):
        icon = "⚽" if self.role == 'att' else "🛡️"
        return f"{icon}{self.strength}"

# --- ロジック関数 ---
def resolve_clash(attackers, defenders, side_name, is_variant):
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
    goals = 0
    remaining_bonus = bonus_gloves.copy()
    current_main_gloves = main_gk_gloves
    save_log = []
    
    for shot_str in shots:
        saved = False
        bonus_candidates = [i for i, g in enumerate(remaining_bonus) if g >= shot_str]
        if bonus_candidates:
            bonus_idx = sorted(bonus_candidates)[0]
            val = remaining_bonus.pop(bonus_idx)
            saved = True
            save_log.append(f"🧤 {gk_name}: 余ったDF(強度{val})がカバーに入りセーブ！")
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

# --- メインアプリ設定 ---
st.set_page_config(page_title="Eleven Match Solver", layout="wide")

# ★ここが重要: スマホでの縦並び強制を解除するカスタムCSS
st.markdown("""
    <style>
    /* モバイル表示時でもカラムを横並びに維持する */
    div[data-testid="column"] {
        width: 50% !important;
        flex: 1 1 auto !important;
        min-width: 10px !important;
    }
    /* カラムの折り返しを防ぐ */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
    }
    /* 入力欄の余白を詰める */
    .stSelectbox, .stNumberInput {
        min-width: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ Eleven Match Solver")

# --- UI構築ヘルパー ---
def render_dynamic_inputs(prefix):
    """
    動的に行を追加・削除できる入力欄 (強制横並び版)
    """
    count_key = f"count_{prefix}"
    if count_key not in st.session_state:
        st.session_state[count_key] = 1
    
    current_count = st.session_state[count_key]
    players = []
    
    role_options = {"ー": None, "⚽攻": "att", "🛡️守": "def"}

    for i in range(current_count):
        # カスタムCSSにより、狭い画面でも必ず横並びになります
        c1, c2 = st.columns([1.2, 1]) 
        
        with c1:
            role_key = st.selectbox(
                f"role_{i}", 
                options=role_options.keys(), 
                key=f"{prefix}_role_{i}", 
                label_visibility="collapsed"
            )
        with c2:
            strength = st.number_input(
                f"str_{i}", 
                min_value=1, max_value=20, value=1, step=1,
                key=f"{prefix}_str_{i}",
                label_visibility="collapsed"
            )
            
        role_val = role_options[role_key]
        if role_val is not None:
            players.append(Player(strength, role_val))
    
    # 追加・削除ボタン
    b_col1, b_col2 = st.columns([1, 1])
    
    def increase():
        st.session_state[count_key] += 1
    def decrease():
        if st.session_state[count_key] > 0:
            st.session_state[count_key] -= 1

    with b_col1:
        st.button("＋追加", key=f"add_{prefix}", on_click=increase, use_container_width=True)
    with b_col2:
        st.button("ー削除", key=f"del_{prefix}", on_click=decrease, use_container_width=True, disabled=(current_count==0))

    return players

# チーム名・設定
with st.expander("⚙️ チーム名・ルール設定", expanded=False):
    col_team1, col_team2 = st.columns(2)
    with col_team1:
        my_team_name = st.text_input("自分のチーム名", value="My Team")
    with col_team2:
        opp_team_name = st.text_input("相手のチーム名", value="Opponent")

    is_variant = st.checkbox('Anti-Moneyball Variant (バリアント) を有効にする', value=True)
    if is_variant:
        st.caption("✅ ON: 最強DF犠牲 / 余りDFグローブ化 / ランダム順序")
    else:
        st.caption("☑️ OFF: 基本ルール")

# GK入力
st.markdown("##### 🧤 ゴールキーパー")
col_gk1, col_gk2 = st.columns(2)

with col_gk1:
    st.info(f"🔵 {my_team_name}")
    st.caption("グローブ / 強度")
    gc1, gc2 = st.columns([1, 1])
    with gc1:
        my_gk_gloves = st.number_input("g", 0, 10, 2, step=1, key="my_gk_g", label_visibility="collapsed")
    with gc2:
        my_gk_str = st.number_input("s", 0, 10, 1, step=1, key="my_gk_s", label_visibility="collapsed")

with col_gk2:
    st.error(f"🔴 {opp_team_name}")
    st.caption("グローブ / 強度")
    gc1, gc2 = st.columns([1, 1])
    with gc1:
        opp_gk_gloves = st.number_input("g", 0, 10, 1, step=1, key="opp_gk_g", label_visibility="collapsed")
    with gc2:
        opp_gk_str = st.number_input("s", 0, 10, 2, step=1, key="opp_gk_s", label_visibility="collapsed")

st.markdown("---")

# ゾーン定義
zones_def = [
    ("Left Wing (左翼)", "LW"),
    ("Right Wing (右翼)", "RW"),
    ("Center Fwd (中央FW)", "CF"),
    ("Center Mid (中央MF)", "CM"),
    ("Center Def (中央DF)", "CD")
]

my_formation = {}
opp_formation = {}

st.markdown("##### 📍 選手配置")
st.caption("左: 役割(攻/守) / 右: 強度")

for z_label, z_id in zones_def:
    opp_label = ""
    if z_id == "LW": opp_label = "(vs 相手RW)"
    elif z_id == "RW": opp_label = "(vs 相手LW)"
    elif z_id == "CF": opp_label = "(vs 相手CD)"
    elif z_id == "CM": opp_label = "(vs 相手CM)"
    elif z_id == "CD": opp_label = "(vs 相手CF)"
    
    with st.expander(f"{z_label} {opp_label}", expanded=False):
        col_my, col_opp = st.columns(2)
        
        # 自分の入力欄
        with col_my:
            st.markdown(f"**🔵 {my_team_name}**")
            my_formation[z_id] = render_dynamic_inputs(f"my_{z_id}")
            
        # 相手の入力欄
        with col_opp:
            st.markdown(f"**🔴 {opp_team_name}**")
            opp_formation[z_id] = render_dynamic_inputs(f"opp_{z_id}")

# 実行ボタン
st.markdown("---")
if st.button("試合解決 (Resolve Match)", type="primary", use_container_width=True):
    st.divider()
    
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
    u_gk_g = my_gk_gloves
    o_gk_g = opp_gk_gloves

    for my_zid in order_list:
        opp_zid = clash_map[my_zid]
        z_label = next(item[0] for item in zones_def if item[1] == my_zid)
        
        u_players = my_formation[my_zid]
        o_players = opp_formation[opp_zid]
        
        st.markdown(f"#### 📍 {z_label}")
        # 選手表示
        u_disp = u_players if u_players else "なし"
        o_disp = o_players if o_players else "なし"
        st.caption(f"{my_team_name}: {u_disp}  vs  {opp_team_name}: {o_disp}")
        
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
