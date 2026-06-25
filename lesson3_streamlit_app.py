import os
import fcntl
from datetime import datetime

import pandas as pd
import streamlit as st


# ==================================================
# 基本設定
# ==================================================

# 回答を保存するCSVファイル名
ANSWER_CSV_FILE = "lesson3_exercise_log.csv"

# CSVで使う列名
CSV_COLUMNS = ["日時", "わからなかった項目", "自由記述"]

# 入力画面に表示する第3回授業の演習問題一覧
EXERCISE_ITEMS = [
    "演習問題1-1: 5科目計の列を追加",
    "演習問題1-2: 欠損値の確認と行削除",
    "演習問題2-1: 学校ID・性別・好きな教科を文字列型に変換",
    "演習問題2-2: 性別コードを男性・女性に置換",
    "演習問題3-1: test_scores_v2.csvを縦に連結",
    "演習問題3-2: school.csvを左外部結合",
    "演習問題3-3: subject.csvを左外部結合して列名変更",
    "演習問題4-1: 75点以上を優と判定する列を追加",
    "演習問題4-2: 5科目計の高い順に並び替え",
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


def save_selected_answers(selected_exercise_items, free_comment):
    # 入力画面で選ばれた問題と自由記述をCSVへ保存する
    # selected_exercise_items は ["演習問題1-1", "演習問題2-1"] のようなリスト
    create_answer_csv_if_needed()

    answered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # チェックされた演習問題は、1つの問題につき1行で保存する
    new_answer_rows = pd.DataFrame(
        {
            "日時": [answered_at for _ in selected_exercise_items],
            "わからなかった項目": selected_exercise_items,
            "自由記述": ["" for _ in selected_exercise_items],
        }
    )

    # 自由記述が入力されている場合は、「その他」として1行追加する
    if free_comment.strip():
        other_answer_row = pd.DataFrame(
            {
                "日時": [answered_at],
                "わからなかった項目": ["その他"],
                "自由記述": [free_comment.strip()],
            }
        )
        new_answer_rows = pd.concat(
            [new_answer_rows, other_answer_row],
            ignore_index=True,
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
    # 保存された回答データから、問題ごとの「わからなかった人数」を集計する
    # 元のデータを直接変更しないように copy() してから加工する
    answer_data = answer_data.copy()

    # 各問題が何回選ばれたかを数える
    misunderstood_count = answer_data["わからなかった項目"].value_counts()

    # 集計結果を表にする
    exercise_summary = pd.DataFrame(
        {
            "わからなかった人数": misunderstood_count,
        }
    ).fillna(0)

    # わからなかった人数が多い順に並べ替えて返す
    return exercise_summary.sort_values("わからなかった人数", ascending=False)


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
st.title("第3回授業 演習問題 わからなかった問題 可視化アプリ")

# 入力画面と集計画面をタブで分ける
tab_input, tab_summary = st.tabs(["入力", "集計"])

with tab_input:
    st.subheader("回答入力")
    with st.form("wakaranai_form", clear_on_submit=True):
        st.write("わからなかった問題にチェックしてください。")
        selected_exercise_items = []

        # 各問題についてチェックボックスを表示する
        for exercise_item in EXERCISE_ITEMS:
            # チェックされた問題だけを保存対象にする
            is_selected = st.checkbox(
                exercise_item,
                key=f"selected_{exercise_item}",
            )

            # チェックが入っている場合だけ、問題名をリストに保存する
            if is_selected:
                selected_exercise_items.append(exercise_item)

        # 選択肢にない内容や、具体的に書きたいことがある場合に使う
        free_comment = st.text_area("その他・自由記述")

        submitted = st.form_submit_button("記録する")

    # 記録ボタンが押されたら、選択内容をCSVに保存する
    if submitted:
        if not selected_exercise_items and not free_comment.strip():
            st.warning("問題を1つ以上選ぶか、自由記述欄に入力してください。")
        else:
            save_selected_answers(selected_exercise_items, free_comment)
            st.success("記録しました。")

with tab_summary:
    # CSVから回答データを読み込み、まだ回答がなければメッセージを表示する
    answer_data = load_answer_data()

    if answer_data.empty:
        st.info("まだデータがありません。")
    else:
        # 回答がある場合は集計表を作り、最も多く選ばれた項目を取り出す
        exercise_summary = create_exercise_summary(answer_data)
        most_common_exercise = exercise_summary.index[0]

        # 重要な数値を画面上部に大きく表示する
        submit_count = answer_data["日時"].nunique()
        selected_count = len(answer_data)

        submit_count_column, selected_count_column, most_common_column = st.columns(3)
        submit_count_column.metric("送信回数", submit_count)
        selected_count_column.metric("選択された数", selected_count)
        most_common_column.metric("最も多かった項目", most_common_exercise)

        st.subheader("集計結果")
        st.dataframe(exercise_summary, use_container_width=True)

        st.subheader("自動コメント")
        st.write(f"最もわからなかった人が多い項目は「{most_common_exercise}」です。")
        st.write("この項目を中心に補足説明やディスカッションを行うとよさそうです。")

        st.subheader("わからなかった人数ランキング")
        display_bar_chart(exercise_summary["わからなかった人数"], "人数")

        st.subheader("その他・自由記述")
        free_comments = answer_data["自由記述"].dropna()
        has_free_comment = False
        for comment in free_comments:
            if str(comment).strip():
                st.write(f"- {comment}")
                has_free_comment = True

        if not has_free_comment:
            st.write("自由記述はまだありません。")

        # 集まった回答データをCSVとしてダウンロードできるようにする
        csv_data = answer_data.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "CSVをダウンロード",
            data=csv_data.encode("utf-8-sig"),
            file_name=ANSWER_CSV_FILE,
            mime="text/csv",
        )
