import sys
sys.path.append('..')

import streamlit as st
from design_of_experiments.application.utils import apply_custom_styles, initialize_session_state
from design_of_experiments.application.doe_tab import doe_tab

import warnings
warnings.simplefilter('ignore')


def main():
    # Streamlitの設定
    st.set_page_config(
        page_title='実験計画法',  # アプリのページタイトル
        page_icon=':lower_left_ballpoint_pen:',  # アプリのアイコン
        layout="wide"  # レイアウトを広げる設定
    )
    st.markdown('### 実験計画法')  # アプリのタイトル表示
    st.markdown("""
    D最適化基準を使った実験計画法による条件算出を行います  
    データがなくこれから取得を始めるときに使います
    1. 範囲を設定または水準を設定
    2. 要素の数だけ設定
    3. サンプル数・基準を設定
    """)  # アプリの説明文を表示
    
    # カスタムスタイルを適用
    apply_custom_styles()
    
    # セッション状態の初期化
    initialize_session_state()
    
    doe_tab()

# メイン関数の実行
if __name__ == '__main__':
    main()