from design_of_experiments.functions import OptimalDesign
import streamlit as st

def input_row(i=0):
    result = []
    c1, c2, c3 = st.columns((1,1,3))
    with c1:
        result.append(st.text_input("要素名"+str(i+1), "要素"+str(i+1)))
    with c2:
        select_type = st.selectbox('選択方法'+str(i+1), ['範囲指定','水準指定'], 0)
        result.append(select_type)
    if select_type=='範囲指定':
        with c3:
            c4,c5,c6 = st.columns(3)
            with c4:
                result.append(st.number_input(
                    '最小値'+str(i+1),
                    min_value=0.,
                    max_value=1000000.,
                    value=0.,
                    step=1.,
                ))
            with c5:
                result.append(st.number_input(
                    '最大値'+str(i+1),
                    min_value=0.,
                    max_value=1000000.,
                    value=100.,
                    step=1.,
                ))
            with c6:
                result.append(st.number_input(
                    '刻み幅'+str(i+1),
                    min_value=0.,
                    max_value=1000000.,
                    value=1.,
                    step=1.,
                ))
    else:
        with c3:
            result.append(st.text_input(
                '要素'+str(i+1)
            ))
    return result

def doe_tab():
    col1, col2, col3, col4, _ = st.columns((1,1,1,1,2))
    with col1:
        opt_type = st.selectbox('基準', ['D','A','E','I','minmax'], 0)
    with col2:
        n_samples = st.number_input('サンプル数',
                        min_value=0,
                        max_value=100,
                        value=10,
                        step=1,)
    
    with col3:
        if st.button('1つ減らす'):
            if st.session_state.n_item>1:
                st.session_state.n_item-=1

    with col4:
        if st.button('1つ増やす'):
            st.session_state.n_item+=1

    input_list = [input_row(i) for i in range(st.session_state.n_item)]

    factor_names = [x[0] for x in input_list]
    x_selet_type = [x[1] for x in input_list]
    x_lower = [x[2] if x[1]=='範囲指定' else None for x in input_list]
    x_upper = [x[3] if x[1]=='範囲指定' else None for x in input_list]
    x_step = [x[4] if x[1]=='範囲指定' else None for x in input_list]

    x_levels = [x[2].split(',') if x[1]=='水準指定' else None for x in input_list]

    col_n, _ = st.columns([1,4])

    with col_n:
        n_const = st.number_input('制約の数',
                        min_value=0,
                        max_value=5,
                        value=0,
                        step=1)        

    const_cols = []
    const_values = []
    for j in range(n_const):
        col5, col6, _ = st.columns([3,1,6])
        with col5:
            const_col = st.multiselect("制約を付ける項目"+str(j), factor_names, [])
            # const_cols = None if len(const_cols)==0 else const_cols
    
        with col6:
            const_value = st.number_input(
                        '和の値'+str(j),
                        min_value=0.,
                        max_value=1000000.,
                        value=0.,
                        step=.01,
                    )
        if len(const_col)>0:
            const_cols.append(const_col)
            const_values.append(None if const_cols is None else const_value)

    if st.button('実験条件計算'):
        opt_func = OptimalDesign()
        opt_func.set(
            factor_names=factor_names,
            x_upper=x_upper,
            x_lower=x_lower,
            x_step=x_step,
            x_levels=x_levels,
            mixture_keys=const_cols,
            sum_target=const_values
        )
        st.session_state.doe_df = df=opt_func.candidate(
            opt_type=opt_type,
            n_iter=1000,
            n_samples=n_samples,
        )
    if st.session_state.doe_df is not None:
        st.write(st.session_state.doe_df)