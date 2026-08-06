import streamlit as st
from typing import List, Optional, Union, Dict, Tuple, Callable, Any
import warnings
warnings.simplefilter('ignore')

def apply_custom_styles():
    """Streamlitアプリケーションにカスタムスタイルを適用する関数。
    
    サイドバーとボタンのスタイルを変更します。
    """
    # サイドバーのスタイルを設定
    sidebar_style = """
    <style>
        section[data-tested="stSidebar"][aria-expanded="true"] {
            width: 700px;
        }
    </style>
    """
    st.markdown(sidebar_style, unsafe_allow_html=True)

    # ボタンのスタイルを設定
    button_css = """
    <style>
      div.stButton > button:first-child  {
        font-weight  : bold;                /* 文字：太字                   */
        color        : #000080;             /* 文字色：ネイビー               */
        font-size    : 100%;                /* 文字サイズ：100%             */
        border       : 5px solid #f36;      /* 枠線：ピンク色で5ピクセルの実線 */
        border-radius: 10px 10px 10px 10px; /* 枠線：半径10ピクセルの角丸     */
        background   : #ddd;                /* 背景色：薄いグレー            */
      }
    </style>
    """
    st.markdown(button_css, unsafe_allow_html=True)


def initialize_session_state() -> None:
    """
    Streamlitのセッションステートを初期化する関数。

    初期化する項目:
        - 'dfrange': None
        - 'dftarget': None
        - 'bo_model': None
        - 'df_predict': None

    Returns:
        None
    """
    if 'n_item' not in st.session_state:
        st.session_state.n_item = 1
    if 'doe_df' not in st.session_state:
        st.session_state.doe_df = None