import os
import fcntl
from datetime import datetime

import pandas as pd
import streamlit as st


# ==================================================
# 基本設定
# ==================================================

# 回答を保存するCSVファイル名
ANSWER_CSV_FILE = "lesson2_exercise_log.csv"

# CSVで使う列名
CSV_COLUMNS = ["日時", "わからなかった項目", "理解度"]

# 入力画面に表示する演習問題の一覧
EXERCISE_ITEMS = [
    "演習問題1-1: CSV読み込みとDataFrame表示",
    "演習問題1-2: 先頭3行の表示",
    "演習問題2-1: locで国語と英語を抽出",
    "演習問題2-2: 学年3かつ数学85点以上を抽出",
    "演習問題2-3: 国語または英語95点以上を抽出",
    "演習問題3-1: 要約統計量の表示",
    "演習問題3-2: 欠損値を含む行の表示",
    "演習問題3-3: 学校別の人数と統計量",
    "演習問題4-1: 国語のヒストグラム作成",
    "演習問題4-2: 英語と数学の散布図作成",
    "その他",
]


# ==================================================
# CSVを準備・読み書きする関数
# ==================================================


def create_answer_csv_if_needed():
    # 回答用CSVがまだ存在しない場合だけ、列名だけが入った空のCSVを作る
    # これにより、初回起動時でも読み込みエラーにならない
    if not os.path.exists(ANSWER_CSV_FILE):
        empty_answer_data = pd.DataFrame(columns=CSV_COLUMNS)
        empty_answer_data.to_csv(ANSWER_CSV_FILE, index=False, encoding="utf-8-sig")


def align_answer_columns(answer_data):
    # CSVの列を、このアプリで使う列名にそろえる
    # もし古いCSVや手作業で編集したCSVに列が足りなくても、ここで補う
    for column_name in CSV_COLUMNS:
        if column_name not in answer_data.columns:
            answer_data[column_name] = None

    # 必要な列だけを、決めた順番で返す
    return answer_data[CSV_COLUMNS]


def load_answer_data():
    # CSVファイルを読み込んで、回答データとして返す
    # 共有ロックを使うことで、他の処理が書き込み中のCSVを読みにくくする
    create_answer_csv_if_needed()

    with open(ANSWER_CSV_FILE, "r", encoding="utf-8-sig") as csv_file:
        fcntl.flock(csv_file, fcntl.LOCK_SH)
        try:
            answer_data = pd.read_csv(csv_file)
            return align_answer_columns(answer_data)
        finally:
            fcntl.flock(csv_file, fcntl.LOCK_UN)


def save_selected_answers(selected_exercise_levels):
    # 入力画面で選ばれた問題と理解度をCSVへ保存する
    # selected_exercise_levels は {"演習問題1-1": 3, "演習問題2-1": 2} のような辞書
    create_answer_csv_if_needed()

    answered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_answer_rows = pd.DataFrame(
        {
            "日時": [answered_at for _ in selected_exercise_levels],
            "わからなかった項目": list(selected_exercise_levels.keys()),
            "理解度": list(selected_exercise_levels.values()),
        }
    )

    # 排他ロックを使い、複数人が同時に記録してもCSVが壊れにくいようにする
    # 1. 現在のCSVを読む
    # 2. 新しい回答を下に追加する
    # 3. CSV全体を書き直す
    with open(ANSWER_CSV_FILE, "r+", encoding="utf-8-sig") as csv_file:
        fcntl.flock(csv_file, fcntl.LOCK_EX)
        try:
            current_answer_data = align_answer_columns(pd.read_csv(csv_file))
            updated_answer_data = pd.concat(
                [current_answer_data, new_answer_rows],
                ignore_index=True,
            )

            csv_file.seek(0)
            csv_file.truncate()
            updated_answer_data.to_csv(csv_file, index=False)
        finally:
            fcntl.flock(csv_file, fcntl.LOCK_UN)


# ==================================================
# 回答データを集計する関数
# ==================================================


def create_exercise_summary(answer_data):
    # 保存された回答データから、問題ごとの集計表を作る
    # 元のデータを直接変更しないように copy() してから加工する
    answer_data = answer_data.copy()

    # 理解度は数値として計算したいので、文字列が混ざっていても数値に変換する
    answer_data["理解度"] = pd.to_numeric(answer_data["理解度"], errors="coerce")

    # 各問題が何回選ばれたかを数える
    misunderstood_count = answer_data["わからなかった項目"].value_counts()

    # 各問題の理解度の平均を求める
    average_understanding = answer_data.groupby("わからなかった項目")["理解度"].mean()

    # 理解度が1または2だった回答だけに絞り、問題ごとに数える
    low_understanding_count = answer_data[answer_data["理解度"] <= 2][
        "わからなかった項目"
    ].value_counts()

    # 3つの集計結果を1つの表にまとめる
    exercise_summary = pd.DataFrame(
        {
            "わからなかった人数": misunderstood_count,
            "平均理解度": average_understanding,
            "理解度1から2の人数": low_understanding_count,
        }
    ).fillna(0)

    # 補足優先度を計算する
    # わからなかった人数が多いほど高くなり、平均理解度が低いほど高くなる
    exercise_summary["補足優先度"] = (
        exercise_summary["わからなかった人数"] * (6 - exercise_summary["平均理解度"])
    )

    # 補足優先度が高い順に並べ替えて返す
    return exercise_summary.sort_values("補足優先度", ascending=False)


def display_bar_chart(chart_series, chart_title):
    # Streamlit標準の棒グラフで表示する
    # 値が大きいものから順に並べ、グラフの名前を付ける
    chart_data = chart_series.sort_values(ascending=False).rename(chart_title)
    st.bar_chart(chart_data)


# ==================================================
# Streamlitの画面を作る
# ==================================================

# アプリ全体のページ設定とタイトル
st.set_page_config(page_title="わからないログ", layout="wide")
st.title("第2回授業 演習問題 わからなかった問題 可視化アプリ")

# 入力画面と集計画面をタブで分ける
tab_input, tab_summary = st.tabs(["入力", "集計"])

with tab_input:
    st.subheader("回答入力")
    with st.form("wakaranai_form", clear_on_submit=True):
        st.write("わからなかった問題にチェックして、理解度を選んでください。")
        selected_exercise_levels = {}

        # 各問題について、チェックボックスと理解度スライダーを横並びで表示する
        for exercise_item in EXERCISE_ITEMS:
            # 左側に問題名、右側に理解度スライダーを置く
            exercise_column, level_column = st.columns([3, 2])

            # チェックされた問題だけを保存対象にする
            is_selected = exercise_column.checkbox(
                exercise_item,
                key=f"selected_{exercise_item}",
            )

            with level_column:
                understanding_level = st.slider(
                    "理解度",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"level_{exercise_item}",
                    label_visibility="collapsed",
                )

            # チェックが入っている場合だけ、問題名と理解度を辞書に保存する
            if is_selected:
                selected_exercise_levels[exercise_item] = understanding_level

        submitted = st.form_submit_button("記録する")

    # 記録ボタンが押されたら、選択内容をCSVに保存する
    if submitted:
        if not selected_exercise_levels:
            st.warning("項目を1つ以上選んでください。")
        else:
            save_selected_answers(selected_exercise_levels)
            st.success("記録しました。")

with tab_summary:
    # CSVから回答データを読み込み、まだ回答がなければメッセージを表示する
    answer_data = load_answer_data()

    if answer_data.empty:
        st.info("まだデータがありません。")
    else:
        # 回答がある場合は集計表を作り、最も補足が必要そうな項目を取り出す
        exercise_summary = create_exercise_summary(answer_data)
        highest_priority_exercise = exercise_summary.index[0]
        highest_priority_average = exercise_summary.loc[
            highest_priority_exercise,
            "平均理解度",
        ]

        # 重要な数値を画面上部に大きく表示する
        record_count_column, priority_column, average_column = st.columns(3)
        record_count_column.metric("記録数", len(answer_data))
        priority_column.metric("最も補足が必要な項目", highest_priority_exercise)
        average_column.metric("平均理解度", round(highest_priority_average, 2))

        st.subheader("集計結果")
        st.dataframe(exercise_summary, use_container_width=True)

        st.subheader("自動コメント")
        st.write(f"最も補足が必要そうな項目は「{highest_priority_exercise}」です。")

        # 平均理解度に応じて、先生向けの簡単なコメントを出す
        if highest_priority_average <= 2:
            st.write("この項目は理解度が低いため、例題を使った説明が必要そうです。")
        elif highest_priority_average <= 3:
            st.write("この項目は少しつまずいている人が多いため、復習すると効果がありそうです。")
        else:
            st.write("理解度は極端に低くありませんが、選んだ人が多いため確認問題を行うとよさそうです。")

        graph_col1, graph_col2 = st.columns(2)
        with graph_col1:
            st.subheader("わからなかった人数ランキング")
            display_bar_chart(exercise_summary["わからなかった人数"], "人数")
        with graph_col2:
            st.subheader("補足説明が必要そうな項目")
            display_bar_chart(exercise_summary["補足優先度"], "補足優先度")

        st.subheader("項目別の平均理解度")
        display_bar_chart(exercise_summary["平均理解度"], "平均理解度")

        # 集まった回答データをCSVとしてダウンロードできるようにする
        csv_data = answer_data.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "CSVをダウンロード",
            data=csv_data.encode("utf-8-sig"),
            file_name=ANSWER_CSV_FILE,
            mime="text/csv",
        )
