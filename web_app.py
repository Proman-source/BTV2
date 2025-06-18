import streamlit as st
import random
from itertools import combinations


# =============================================================================
# == BACKEND TOURNAMENT LOGIC (Komplett unverändert)
# =============================================================================
def is_match_valid(team1, team2, past_partners, past_opponents):
    if frozenset(team1) in past_partners or frozenset(team2) in past_partners: return False
    for p1 in team1:
        for p2 in team2:
            if frozenset([p1, p2]) in past_opponents: return False
    return True


def pair_up_teams(teams, past_partners, past_opponents):
    available = list(teams);
    random.shuffle(available)
    pairings = []
    while len(available) >= 2:
        team1 = available.pop(0)
        found_opponent = False
        for i, team2 in enumerate(available):
            if is_match_valid(team1, team2, past_partners, past_opponents):
                pairings.append((team1, available.pop(i)));
                found_opponent = True;
                break
        if not found_opponent: return None
    return pairings


def generate_round(participants, previous_rounds, max_retries=100):
    num_participants = len(participants)
    num_triplette_matches, rem_participants = 0, num_participants
    while rem_participants > 0 and rem_participants % 4 != 0:
        rem_participants -= 6;
        num_triplette_matches += 1
    if rem_participants < 0: return None
    num_doublette_matches = rem_participants // 4
    past_partners, past_opponents = set(), set()
    for past_round in previous_rounds:
        for match_info in past_round:
            t1, t2 = match_info["match"]
            past_partners.add(frozenset(t1));
            past_partners.add(frozenset(t2))
            for p1 in t1:
                for p2 in t2: past_opponents.add(frozenset([p1, p2]))
    for _ in range(max_retries):
        shuffled = random.sample(participants, k=num_participants)
        triplette_players, doublette_players = shuffled[:num_triplette_matches * 6], shuffled[
                                                                                     num_triplette_matches * 6:]
        triplette_teams = [triplette_players[i:i + 3] for i in range(0, len(triplette_players), 3)]
        doublette_teams = [doublette_players[i:i + 2] for i in range(0, len(doublette_players), 2)]
        triplette_pairings, doublette_pairings = pair_up_teams(triplette_teams, past_partners,
                                                               past_opponents), pair_up_teams(doublette_teams,
                                                                                              past_partners,
                                                                                              past_opponents)
        if triplette_pairings is not None and doublette_pairings is not None:
            round_data = [{"type": "Triplette", "match": m} for m in triplette_pairings]
            round_data.extend([{"type": "Doublette", "match": m} for m in doublette_pairings])
            return round_data
    return None


def initialize_scores(participants):
    return {person: {"GP": 0, "KP": 0} for person in participants}


def update_scores(all_results, participant_scores, round_byes):
    for (team1, team2), (score1, score2) in all_results.items():
        diff = abs(score1 - score2)
        if score1 > score2:
            for p in team1: participant_scores[p]["GP"] += 2; participant_scores[p]["KP"] += diff
        elif score2 > score1:
            for p in team2: participant_scores[p]["GP"] += 2; participant_scores[p]["KP"] += diff
        else:
            for p in team1 + team2: participant_scores[p]["GP"] += 1
    bye_points_gp, bye_points_kp = 2, 5
    for bye in round_byes:
        if bye: participant_scores[bye]["GP"] += bye_points_gp; participant_scores[bye]["KP"] += bye_points_kp


def get_ranking_text(participant_scores):
    sorted_participants = sorted(participant_scores.items(), key=lambda x: (-x[1]["GP"], -x[1]["KP"]))
    ranking_lines = ["Endgültige Rangliste:", "=" * 35]
    last_gp, last_kp, rank = None, None, 0
    for i, (p, s) in enumerate(sorted_participants):
        gp, kp = s["GP"], s["KP"]
        if gp != last_gp or kp != last_kp: rank = i + 1
        ranking_lines.append(f"{rank}. {p} (GP: {gp}, KP: {kp})")
        last_gp, last_kp = gp, kp
    return "\n".join(ranking_lines)


# =============================================================================
# == Streamlit Web App Interface
# =============================================================================

st.set_page_config(page_title="Super Mêlée Turnier", layout="wide")

# Session State Initialisierung
if 'stage' not in st.session_state:
    st.session_state.stage = 'setup'
if 'match_results' not in st.session_state:
    st.session_state.match_results = {}
if 'selected_match' not in st.session_state:
    st.session_state.selected_match = None


# --- STUFE 1: SETUP ---
def setup_stage():
    st.title("Boule Super Mêlée Generator  Turnier-Setup")
    participant_count = st.selectbox("Anzahl der Teilnehmenden auswählen:", options=list(range(16, 41)), index=0)
    if st.button("Weiter zur Namenseingabe", type="primary"):
        st.session_state.participant_count = participant_count
        st.session_state.stage = 'name_input'
        st.rerun()


# --- STUFE 2: NAMENSEINGABE ---
def name_input_stage():
    st.title("Namen der Teilnehmenden eingeben")
    with st.form("name_form"):
        p_names = [st.text_input(f"Teilnehmende/r {i + 1}:", key=f"name_{i}") for i in
                   range(st.session_state.participant_count)]
        if st.form_submit_button("Turnier generieren", type="primary"):
            if not all(n.strip() for n in p_names):
                st.error("Bitte alle Namen ausfüllen.")
            elif len(set(p.strip() for p in p_names)) != len(p_names):
                st.error("Jeder Name muss einzigartig sein.")
            else:
                with st.spinner("Generiere alle Runden..."):
                    participants, all_rounds, round_byes, bye_tracker = [n.strip() for n in p_names], [], [], set()
                    success = True
                    for _ in range(3):
                        current_p, bye = list(participants), None
                        if len(current_p) % 2 != 0:
                            possible = [p for p in current_p if p not in bye_tracker]
                            if not possible: bye_tracker.clear(); possible = current_p
                            bye = random.choice(possible);
                            bye_tracker.add(bye);
                            current_p.remove(bye)
                        round_byes.append(bye)
                        round_data = generate_round(current_p, all_rounds)
                        if round_data is None and current_p:
                            st.error(f"Generierungsfehler in Runde {len(all_rounds) + 1}.");
                            success = False;
                            break
                        all_rounds.append(round_data or [])
                if success:
                    st.session_state.participants, st.session_state.all_rounds_data, st.session_state.round_byes = participants, all_rounds, round_byes
                    st.session_state.stage = 'results_input'
                    st.rerun()


# --- STUFE 3: ERGEBNISEINGABE ---
def results_input_stage():
    st.title("Paarungen & Ergebnisse")
    if st.session_state.selected_match:
        display_single_match_page()
    else:
        display_results_lobby()


def display_results_lobby():
    """Zeigt die Hauptseite mit allen Spielen und Buttons an."""
    total_matches = sum(len(r) for r in st.session_state.all_rounds_data)
    # Kleiner Fortschrittsbalken
    progress = len(st.session_state.match_results) / total_matches if total_matches > 0 else 0
    st.progress(progress,
                text=f"Ergebnisse für {len(st.session_state.match_results)} von {total_matches} Spielen eingetragen.")

    for i, round_data in enumerate(st.session_state.all_rounds_data):
        with st.expander(f"**Runde {i + 1}**", expanded=True):
            bye_recipient = st.session_state.round_byes[i]
            if bye_recipient: st.info(f"Freilos: **{bye_recipient}**")
            if not round_data: st.write("Keine Spiele."); continue

            for match_info in round_data:
                team1, team2 = match_info["match"]
                match_key = f"{','.join(sorted(team1))}-vs-{','.join(sorted(team2))}"

                col1, col2 = st.columns([2, 1])
                label_text = f"**[{match_info['type']}]** {', '.join(team1)} vs {', '.join(team2)}"
                col1.markdown(label_text, unsafe_allow_html=True)

                # *** HIER IST DIE ÄNDERUNG ***
                if match_key in st.session_state.match_results:
                    score = st.session_state.match_results[match_key]
                    # Zeige Ergebnis und einen "Ändern"-Button an
                    score_col, button_col = col2.columns([2, 1])
                    score_col.success(f"{score}")
                    if button_col.button("Ändern", key=f"edit_{match_key}", use_container_width=True):
                        st.session_state.selected_match = match_key
                        st.rerun()
                else:
                    # Zeige wie bisher den "Eintragen"-Button an
                    if col2.button("Eintragen", key=f"btn_{match_key}", use_container_width=True):
                        st.session_state.selected_match = match_key
                        st.rerun()

    st.write("---")
    if len(st.session_state.match_results) == total_matches and total_matches > 0:
        if st.button("Alle Ergebnisse sind da! Rangliste berechnen.", type="primary", use_container_width=True):
            all_results = {}
            for key, score_text in st.session_state.match_results.items():
                t1_names, t2_names = key.split('-vs-')
                t1, t2 = tuple(t1_names.split(',')), tuple(t2_names.split(','))
                s1, s2 = map(int, score_text.split(':'))
                all_results[(t1, t2)] = (s1, s2)

            scores = initialize_scores(st.session_state.participants)
            update_scores(all_results, scores, st.session_state.round_byes)
            st.session_state.ranking = get_ranking_text(scores)
            st.session_state.stage = 'ranking_display'
            st.rerun()


def display_single_match_page():
    """Zeigt eine Seite nur für die Eingabe EINES Ergebnisses."""
    match_key = st.session_state.selected_match
    t1_names, t2_names = match_key.split('-vs-')
    team1, team2 = t1_names.split(','), t2_names.split(',')

    st.header(f"Ergebnis für {' & '.join(team1)} vs {' & '.join(team2)}")

    with st.form("single_match_form"):
        # *** HIER IST DIE ZWEITE ÄNDERUNG ***
        # Trägt den bereits gespeicherten Wert in das Feld ein, falls vorhanden
        existing_value = st.session_state.match_results.get(match_key, "")
        score_input = st.text_input("Ergebnis (z.B. 13:10):", value=existing_value, key=f"score_input_{match_key}")

        # Buttons in Spalten für schöneres Layout
        col1, col2 = st.columns(2)
        if col1.form_submit_button("Speichern & zurück zur Übersicht", type="primary", use_container_width=True):
            try:
                s1, s2 = map(int, score_input.split(':'))
                st.session_state.match_results[match_key] = f"{s1}:{s2}"
                st.session_state.selected_match = None  # Wichtig: Auswahl zurücksetzen
                st.rerun()
            except (ValueError, IndexError):
                if score_input:
                    st.error("Bitte Ergebnis im Format 'Punkte:Punkte' eingeben, z.B. '13:10'.")

        if col2.form_submit_button("Abbrechen & zurück zur Übersicht", use_container_width=True):
            st.session_state.selected_match = None  # Wichtig: Auswahl zurücksetzen
            st.rerun()


# --- STUFE 4: RANGLISTENANZEIGE ---
def ranking_display_stage():
    st.title("Turnier beendet!");
    st.balloons()
    st.subheader("Endgültige Rangliste")
    st.code(st.session_state.ranking, language=None)
    if st.button("Neues Turnier starten", use_container_width=True):
        st.session_state.clear();
        st.session_state.stage = 'setup'
        st.rerun()


# Haupt-Router, der entscheidet, welche Funktion aufgerufen wird
if st.session_state.stage == 'setup':
    setup_stage()
elif st.session_state.stage == 'name_input':
    name_input_stage()
elif st.session_state.stage == 'results_input':
    results_input_stage()
elif st.session_state.stage == 'ranking_display':
    ranking_display_stage()
