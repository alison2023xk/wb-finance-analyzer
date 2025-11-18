import io
from pathlib import Path

import pandas as pd
import streamlit as st

# ==============================
# 1. 字段映射 & 枚举配置
# ==============================

COLUMN_MAP = {
    "Обоснование для оплаты": "reason_for_payment",
    "Виды логистики, штрафов и корректировок ВВ": "logistics_fee_type",
    "Баркод": "barcode",
    "Артикул поставщика": "supplier_sku",
    "К перечислению Продавцу за реализованный Товар": "amount_payable_goods",
    "Вайлдберриз реализовал Товар (Пр)": "wb_gmv",
    "Цена розничная": "retail_price_total",
    "Услуги по доставке товара покупателю": "delivery_to_customer",
    "Общая сумма штрафов": "fine_total",
    "Компенсация скидки по программе лояльности": "loyalty_discount_comp",
    "Стоимость участия в программе лояльности": "loyalty_service_fee",
    "Сумма удержанная за начисленные баллы программы лояльности": "loyalty_points_deduction",
    "Кол-во": "quantity",
    "Склад": "warehouse",
}

REASON_SALES = ["Продажа"]
REASON_RETURNS = ["Возврат"]

FEE_TYPE_MAP = {
    "sales_logistics": {
        "ru_types": ["К клиенту при продаже"],
        "desc": "销售成功对应的正向物流费用",
    },
    "cancel_logistics_forward": {
        "ru_types": ["К клиенту при отмене"],
        "desc": "已发货但订单被取消，正向物流费用",
    },
    "cancel_logistics_backward": {
        "ru_types": ["От клиента при отмене"],
        "desc": "订单取消后，商品退回仓库的逆向物流费用",
    },
    "loyalty_points_deduction": {
        "ru_types": ["Сумма удержанная за начисленные баллы программы лояльности"],
        "desc": "为买家积累积分而从卖家账户扣除的金额",
    },
    "loyalty_service_fee": {
        "ru_types": ["Стоимость участия в программе лояльности"],
        "desc": "参与忠诚计划本身的服务费用",
    },
    "size_penalty": {
        "ru_types": ["Занижение фактических габаритов упаковки товара"],
        "desc": "因低报包装尺寸导致的罚款",
    },
    "defect_compensation": {
        "ru_types": ["Компенсация скидки по программе лояльности"],
        "desc": "平台对折扣/品质问题的某种补偿（暂按费用处理）",
    },
    "loyalty_refund_from_customer": {
        "ru_types": ["От клиента при возврате"],
        "desc": "与忠诚计划相关的客户返还/补偿",
    },
}

FORWARD_CANCEL_TYPES = FEE_TYPE_MAP["cancel_logistics_forward"]["ru_types"]
BACKWARD_CANCEL_TYPES = FEE_TYPE_MAP["cancel_logistics_backward"]["ru_types"]


# ==============================
# 2. 读 & 合并当前周上传的所有报表（第0步）
# ==============================

def load_week_data_from_upload(files) -> pd.DataFrame:
    """从网页上传的多个 .xlsx 中读取并合并为一个 DataFrame。"""
    dfs = []
    for f in files:
        df_raw = pd.read_excel(f)
        df = df_raw.rename(columns=COLUMN_MAP)
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)

    for col in [
        "amount_payable_goods",
        "wb_gmv",
        "retail_price_total",
        "delivery_to_customer",
        "fine_total",
        "loyalty_discount_comp",
        "loyalty_service_fee",
        "loyalty_points_deduction",
        "quantity",
    ]:
        if col not in combined_df.columns:
            combined_df[col] = 0

    return combined_df


# ==============================
# 3. 步骤1：销售统计（按SKU）
# ==============================

def load_cost_table(cost_file) -> pd.DataFrame:
    """
    从上传的采购成本文件中读取 SKU 对应的单件采购成本。
    文件要求至少两列：
      - SKU 或 sku 或 barcode（任意一个）
      - 采购成本 / cost / purchase_cost（任意一个）
    """
    df = pd.read_excel(cost_file)

    # 列名统一成小写方便匹配
    col_map = {c: str(c).strip().lower() for c in df.columns}
    df = df.rename(columns=col_map)

    # 找 SKU 列
    sku_col = None
    for cand in ["sku", "barcode", "条码"]:
        if cand in df.columns:
            sku_col = cand
            break
    if sku_col is None:
        raise ValueError("采购成本文件中找不到 SKU 列，请确保包含 'SKU' 或 'sku' 或 'barcode' 字段。")

    # 找成本列
    cost_col = None
    for cand in ["采购成本", "cost", "purchase_cost"]:
        if cand in df.columns:
            cost_col = cand
            break
    if cost_col is None:
        raise ValueError("采购成本文件中找不到成本列，请确保包含 '采购成本' 或 'cost' 字段。")

    cost_df = df[[sku_col, cost_col]].copy()
    cost_df = cost_df.rename(columns={
        sku_col: "SKU",
        cost_col: "unit_cost",
    })

    # 同一个 SKU 如果出现多次，取平均或者最大值，这里先用平均
    cost_df = (
        cost_df
        .groupby("SKU", as_index=False)["unit_cost"]
        .mean()
    )

    return cost_df
def compute_profit_by_sku(net_sales_df: pd.DataFrame,
                          sales_logistics_by_sku: pd.DataFrame,
                          cancel_logistics_by_sku: pd.DataFrame,
                          cost_df: pd.DataFrame) -> pd.DataFrame:
    """
    生成 6 列的利润表：
    SKU / 销售件数 / 商品应付金额 / 物流费用 / 采购成本 / 利润
    """

    # 1) 先从净销售表中取出需要的字段
    base = net_sales_df.copy()

    # 当前 net_sales_df 的结构是：SKU / 件数 / 商品应付金额 / 前台销售额 / 后台定价
    base = base.rename(columns={
        "件数": "sales_qty",
        "商品应付金额": "amount_payable",
    })

    # 2) 合并销售物流费用
    sales_log = sales_logistics_by_sku.rename(
        columns={"barcode": "SKU"}
    )[["SKU", "sales_logistics_sum"]].copy()

    # 3) 合并取消/退货相关的物流费用（这里用 total_cancel_logistics）
    cancel_log = cancel_logistics_by_sku.rename(
        columns={"barcode": "SKU"}
    )[["SKU", "total_cancel_logistics"]].copy()
    cancel_log = cancel_log.rename(columns={"total_cancel_logistics": "cancel_logistics_sum"})

    merged = (
        base
        .merge(sales_log, on="SKU", how="left")
        .merge(cancel_log, on="SKU", how="left")
    )

    merged["sales_logistics_sum"] = merged["sales_logistics_sum"].fillna(0)
    merged["cancel_logistics_sum"] = merged["cancel_logistics_sum"].fillna(0)

    # 总物流费用 = 销售物流 + 取消/退货物流
    merged["logistics_total"] = merged["sales_logistics_sum"] + merged["cancel_logistics_sum"]

    # 4) 合并采购成本（单件成本）
    cost_df = cost_df.copy()
    merged = merged.merge(cost_df, on="SKU", how="left")
    merged["unit_cost"] = merged["unit_cost"].fillna(0)

    # 采购成本总额 = 单件成本 * 销售件数
    merged["purchase_total"] = merged["unit_cost"] * merged["sales_qty"]

    # 5) 计算利润
    merged["profit"] = merged["amount_payable"] - merged["logistics_total"] - merged["purchase_total"]

    # 6) 按你要的 6 列输出，并使用中文表头
    profit_df = pd.DataFrame({
        "SKU": merged["SKU"],
        "销售件数": merged["sales_qty"],
        "商品应付金额": merged["amount_payable"],
        "物流费用": merged["logistics_total"],
        "采购成本": merged["purchase_total"],
        "利润": merged["profit"],
    })

    # 可以按利润或 SKU 排序，这里先按 SKU
    profit_df = profit_df.sort_values("SKU")

    return profit_df

def compute_sales_by_sku(df: pd.DataFrame) -> pd.DataFrame:
    sales_df = df[df["reason_for_payment"].isin(REASON_SALES)].copy()

    grouped = (
        sales_df
        .groupby("barcode", dropna=False)
        .agg(
            sales_qty=("barcode", "count"),
            amount_payable_sum=("amount_payable_goods", "sum"),
            wb_gmv_sum=("wb_gmv", "sum"),
            retail_price_sum=("retail_price_total", "sum"),
        )
        .reset_index()
        .sort_values("barcode")
    )

    grouped["discount_rate"] = 1 - grouped["wb_gmv_sum"] / grouped["retail_price_sum"]
    grouped["discount_rate"] = grouped["discount_rate"].round(4)

    return grouped


# ==============================
# 4. 步骤2：退货统计（按SKU）
# ==============================

def compute_returns_by_sku(df: pd.DataFrame) -> pd.DataFrame:
    returns_df = df[df["reason_for_payment"].isin(REASON_RETURNS)].copy()

    grouped = (
        returns_df
        .groupby("barcode", dropna=False)
        .agg(
            return_qty=("barcode", "count"),
            amount_return_sum=("amount_payable_goods", "sum"),
            wb_gmv_return_sum=("wb_gmv", "sum"),
            retail_price_return_sum=("retail_price_total", "sum"),
        )
        .reset_index()
        .sort_values("barcode")
    )
    return grouped


# ==============================
# 5. 步骤3：净销售（销售 − 退货）
# ==============================

def compute_net_sales_by_sku(sales_by_sku: pd.DataFrame,
                             returns_by_sku: pd.DataFrame) -> pd.DataFrame:
    """
    计算每个 SKU 的净销售，只输出净销售相关字段，并用中文表头：
    SKU、件数、商品应付金额、前台销售额、后台定价
    """
    merged = pd.merge(
        sales_by_sku,
        returns_by_sku,
        on="barcode",
        how="outer",
    ).fillna(0)

    # 计算净值
    merged["net_qty"] = merged["sales_qty"] - merged["return_qty"]
    merged["net_amount_payable"] = merged["amount_payable_sum"] - merged["amount_return_sum"]
    merged["net_wb_gmv"] = merged["wb_gmv_sum"] - merged["wb_gmv_return_sum"]
    merged["net_retail_price"] = merged["retail_price_sum"] - merged["retail_price_return_sum"]

    # 只保留需要的列
    net_df = merged[["barcode", "net_qty", "net_amount_payable", "net_wb_gmv", "net_retail_price"]].copy()

    # 重命名为中文表头
    net_df = net_df.rename(columns={
        "barcode": "SKU",
        "net_qty": "件数",
        "net_amount_payable": "商品应付金额",
        "net_wb_gmv": "前台销售额",
        "net_retail_price": "后台定价",
    })

    # 按 SKU 排序
    net_df = net_df.sort_values("SKU")

    # 在表格首行添加总计
    total_row = {
        "SKU": "总计",
        "件数": net_df["件数"].sum(),
        "商品应付金额": net_df["商品应付金额"].sum(),
        "前台销售额": net_df["前台销售额"].sum(),
        "后台定价": net_df["后台定价"].sum(),
    }
    net_df = pd.concat(
        [pd.DataFrame([total_row]), net_df],
        ignore_index=True,
    )

    return net_df



# ==============================
# 6. 步骤4：销售物流费用（按SKU）
# ==============================

def compute_sales_logistics_by_sku(df: pd.DataFrame) -> pd.DataFrame:
    log_df = df[df["logistics_fee_type"].isin(FEE_TYPE_MAP["sales_logistics"]["ru_types"])].copy()
    log_df = log_df[log_df["delivery_to_customer"] != 0]

    grouped = (
        log_df
        .groupby("barcode", dropna=False)
        .agg(
            sales_logistics_count=("barcode", "count"),
            sales_logistics_sum=("delivery_to_customer", "sum"),
        )
        .reset_index()
        .sort_values("barcode")
    )

    grouped["sales_logistics_per_unit"] = (
        grouped["sales_logistics_sum"] / grouped["sales_logistics_count"]
    ).round(4)

    return grouped


# ==============================
# 7. 步骤5：取消订单物流费用（按SKU）
# ==============================

def compute_cancel_logistics_by_sku(df: pd.DataFrame) -> pd.DataFrame:
    forward_df = df[df["logistics_fee_type"].isin(FORWARD_CANCEL_TYPES)].copy()
    backward_df = df[df["logistics_fee_type"].isin(BACKWARD_CANCEL_TYPES)].copy()

    forward_g = (
        forward_df
        .groupby("barcode", dropna=False)
        .agg(
            forward_count=("barcode", "count"),
            forward_logistics_sum=("delivery_to_customer", "sum"),
        )
        .reset_index()
    )

    backward_g = (
        backward_df
        .groupby("barcode", dropna=False)
        .agg(
            backward_count=("barcode", "count"),
            backward_logistics_sum=("delivery_to_customer", "sum"),
        )
        .reset_index()
    )

    merged = pd.merge(forward_g, backward_g, on="barcode", how="outer").fillna(0)

    merged["total_cancel_records"] = merged["forward_count"] + merged["backward_count"]
    merged["cancel_qty"] = merged["total_cancel_records"] / 2

    merged["total_cancel_logistics"] = (
        merged["forward_logistics_sum"] + merged["backward_logistics_sum"]
    )

    merged["cancel_logistics_per_unit"] = merged["total_cancel_logistics"] / merged["cancel_qty"]
    merged.loc[merged["cancel_qty"] == 0, "cancel_logistics_per_unit"] = 0
    merged["cancel_logistics_per_unit"] = merged["cancel_logistics_per_unit"].round(4)

    return merged.sort_values("barcode")


# ==============================
# 8. 步骤6：每个 SKU 的取消率
# ==============================

def compute_cancellation_rate(sales_by_sku: pd.DataFrame,
                              cancel_log_by_sku: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(
        sales_by_sku[["barcode", "sales_qty"]],
        cancel_log_by_sku[["barcode", "cancel_qty"]],
        on="barcode",
        how="outer",
    ).fillna(0)

    merged["total_orders"] = merged["sales_qty"] + merged["cancel_qty"]
    merged["cancellation_rate"] = merged["cancel_qty"] / merged["total_orders"]
    merged.loc[merged["total_orders"] == 0, "cancellation_rate"] = 0
    merged["cancellation_rate"] = merged["cancellation_rate"].round(4)

    return merged.sort_values("barcode")


# ==============================
# 9. 步骤7：费用分类汇总
# ==============================

def compute_fee_summary(df: pd.DataFrame,
                        profit_by_sku: pd.DataFrame) -> pd.DataFrame:
    """
    费用汇总表：
      只保留两列：description / total_fee
      行包括：
        - 各费用类别（物流、罚款、忠诚计划等）
        - 采购成本（来自净利润表）
        - 总费用（以上全部之和）
    """
    rows = []

    # 1) 各费用类别（不包含采购成本）
    for cat, info in FEE_TYPE_MAP.items():
        ru_types = info["ru_types"]
        sub = df[df["logistics_fee_type"].isin(ru_types)].copy()
        if sub.empty:
            fine_sum = 0
            loyalty_service_sum = 0
            loyalty_points_sum = 0
            logistics_sum = 0
        else:
            fine_sum = sub["fine_total"].sum()
            loyalty_service_sum = sub["loyalty_service_fee"].sum()
            loyalty_points_sum = sub["loyalty_points_deduction"].sum()
            logistics_sum = sub["delivery_to_customer"].sum()

        # total_fee = 真正的费用：罚款 + 忠诚服务费 + 积分扣费 + 物流费用
        total_fee = (
            fine_sum
            + loyalty_service_sum
            + loyalty_points_sum
            + logistics_sum
        )

        rows.append({
            "description": info["desc"],
            "total_fee": total_fee,
        })

    # 2) 采购成本：来自净利润表中的“采购成本”列
    if "采购成本" in profit_by_sku.columns:
        purchase_total = float(profit_by_sku["采购成本"].sum())
    else:
        purchase_total = 0.0

    rows.append({
        "description": "采购成本",
        "total_fee": purchase_total,
    })

    # 3) 总费用 = 上面所有 total_fee 之和
    total_all = sum(r["total_fee"] for r in rows)

    rows.append({
        "description": "总费用",
        "total_fee": total_all,
    })

    fee_df = pd.DataFrame(rows, columns=["description", "total_fee"])

    return fee_df



# ==============================
# 10. 步骤8：总览 & 平台应付金额
# ==============================

def compute_final_overview(df: pd.DataFrame,
                           fee_summary: pd.DataFrame) -> pd.DataFrame:
    sales_df = df[df["reason_for_payment"].isin(REASON_SALES)]
    returns_df = df[df["reason_for_payment"].isin(REASON_RETURNS)]

    total_sales_qty = len(sales_df)
    total_return_qty = len(returns_df)

    total_sales_amount = sales_df["amount_payable_goods"].sum()
    total_return_amount = returns_df["amount_payable_goods"].sum()

    net_sales_amount = total_sales_amount - total_return_amount

    total_fee_amount = float(
          fee_summary.loc[fee_summary["description"] == "总费用", "total_fee"].iloc[0]
    )
    final_payable_amount = net_sales_amount - total_fee_amount

    overview = pd.DataFrame(
        [
            {"metric": "total_sales_qty", "value": total_sales_qty},
            {"metric": "total_return_qty", "value": total_return_qty},
            {"metric": "total_sales_amount", "value": total_sales_amount},
            {"metric": "total_return_amount", "value": total_return_amount},
            {"metric": "net_sales_amount", "value": net_sales_amount},
            {"metric": "total_fee_amount", "value": total_fee_amount},
            {"metric": "final_payable_amount", "value": final_payable_amount},
        ]
    )

    # 英文指标 -> 中文名称
    metric_zh_map = {
        "total_sales_qty": "销售件数",
        "total_return_qty": "退货件数",
        "total_sales_amount": "销售结算金额（含退货前）",
        "total_return_amount": "退货结算金额",
        "net_sales_amount": "净销售结算金额",
        "total_fee_amount": "费用总额",
        "final_payable_amount": "平台最终应付金额",
    }

    overview["metric_zh"] = overview["metric"].map(metric_zh_map)

    # 调整列顺序：中文放前面
    overview = overview[["metric_zh", "metric", "value"]]

    return overview



# ==============================
# 11. 生成 summary.xlsx 供下载
# ==============================

def build_summary_excel(week_label: str,
                        sales_by_sku: pd.DataFrame,
                        returns_by_sku: pd.DataFrame,
                        net_sales_by_sku: pd.DataFrame,
                        sales_logistics_by_sku: pd.DataFrame,
                        cancel_logistics_by_sku: pd.DataFrame,
                        cancellation_rate_by_sku: pd.DataFrame,
                        fee_summary: pd.DataFrame,
                        overview: pd.DataFrame,
                        profit_by_sku: pd.DataFrame) -> bytes:

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sales_by_sku.to_excel(writer, sheet_name="Sales_by_SKU", index=False)
        returns_by_sku.to_excel(writer, sheet_name="Returns_by_SKU", index=False)
        net_sales_by_sku.to_excel(writer, sheet_name="Net_Sales_by_SKU", index=False)
        sales_logistics_by_sku.to_excel(writer, sheet_name="Logistics_Sales", index=False)
        cancel_logistics_by_sku.to_excel(writer, sheet_name="Logistics_Cancellations", index=False)
        cancellation_rate_by_sku.to_excel(writer, sheet_name="Cancellation_Rate", index=False)
        fee_summary.to_excel(writer, sheet_name="Fee_Summary", index=False)
        overview.to_excel(writer, sheet_name="Final_Overview", index=False)
        profit_by_sku.to_excel(writer, sheet_name="Profit_by_SKU", index=False)

    output.seek(0)
    return output.getvalue()


# ==============================
# 12. Streamlit 网页界面
# ==============================

def main():
    st.set_page_config(page_title="WB 每周财务报表分析", layout="wide")

    st.title("WB 每周财务报表自动汇总（可视化版）")

    st.markdown(
        """
        使用说明：
        1. 在下方上传本周的 **2 份 WB 财务报表**（境内 + 境外），均为 `.xlsx` 格式；
        2. 输入对应的周标签（例如：`0311-0911`）；
        3. 点击“开始分析”，稍等即可查看各个结果表；
        4. 可以在页面底部 **下载 summary.xlsx** 保存。
        """
    )
    week_label = st.text_input("本次分析的名称/标签（例如：20251103-1109 或 Q4汇总）", value="20251103-1109")

    uploaded_files = st.file_uploader(
    "上传要分析的 WB 财务报表（可以一次上传多周、多份，境内+境外混合）",
    type=["xlsx"],
    accept_multiple_files=True,
    )

    selected_files = []

    if uploaded_files:
        # 显示上传的文件列表
        st.markdown("### 已上传的文件")
        file_info_rows = []
        for f in uploaded_files:
            name = f.name
            stem = Path(name).stem
            # 简单从文件名里识别“境内/境外”和时间段（可根据你的命名规则调整）
            if "境内" in stem:
                region = "境内"
                period = stem.replace("境内", "")
            elif "境外" in stem:
                region = "境外"
                period = stem.replace("境外", "")
            else:
                region = "未知"
                period = stem
            file_info_rows.append({"文件名": name, "期间": period, "区域": region})

        st.dataframe(pd.DataFrame(file_info_rows), use_container_width=True)

        # 让你选择要分析哪些文件（可多选）
        file_labels = [f.name for f in uploaded_files]
        selected_labels = st.multiselect(
            "选择要参与本次分析的报表（可多选，不选视为全部）",
            file_labels,
            default=file_labels,  # 默认全部勾选
        )
        selected_files = [f for f in uploaded_files if f.name in selected_labels]

    cost_file = st.file_uploader(
    "上传采购成本文件（两列：SKU / 采购成本）",
    type=["xlsx"],
    accept_multiple_files=False,
    )

    if st.button("开始分析"):

        if not selected_files:
            st.error("请先上传文件并在列表中选择至少 1 份要分析的报表。")
            return

        # 第0步：只合并“被你选中”的文件
        df = load_week_data_from_upload(selected_files)

        st.success(f"已成功读取 {len(selected_files)} 个文件，合并后共有 {len(df)} 行记录。")

        # 步骤1～5计算
        sales_by_sku = compute_sales_by_sku(df)
        returns_by_sku = compute_returns_by_sku(df)
        net_sales_by_sku = compute_net_sales_by_sku(sales_by_sku, returns_by_sku)
        sales_logistics_by_sku = compute_sales_logistics_by_sku(df)
        cancel_logistics_by_sku = compute_cancel_logistics_by_sku(df)
        cancellation_rate_by_sku = compute_cancellation_rate(sales_by_sku, cancel_logistics_by_sku)
        # 2) 处理采购成本表
        if cost_file is not None:
            try:
                cost_df = load_cost_table(cost_file)
            except Exception as e:
                st.error(f"读取采购成本文件时出错：{e}")
                cost_df = pd.DataFrame(columns=["SKU", "unit_cost"])
        else:
            st.warning("未上传采购成本文件，本次利润计算中的采购成本将视为 0。")
            cost_df = pd.DataFrame(columns=["SKU", "unit_cost"])

        # 3) 计算利润表（这里的 net_sales_by_sku 已经是中文表头版本）
        profit_by_sku = compute_profit_by_sku(
            net_sales_by_sku,
            sales_logistics_by_sku,
            cancel_logistics_by_sku,
            cost_df,
        )

        # 4) 费用汇总（把采购成本也算进去）
        fee_summary = compute_fee_summary(df, profit_by_sku)

        # 5) 总览（使用新的 fee_summary）
        overview = compute_final_overview(df, fee_summary)

        # 顶部总览指标
        st.subheader("本周关键指标总览")
        col1, col2, col3, col4 = st.columns(4)
        total_sales_qty = int(overview.loc[overview["metric"] == "total_sales_qty", "value"].iloc[0])
        total_return_qty = int(overview.loc[overview["metric"] == "total_return_qty", "value"].iloc[0])
        net_sales_amount = float(overview.loc[overview["metric"] == "net_sales_amount", "value"].iloc[0])
        final_payable_amount = float(overview.loc[overview["metric"] == "final_payable_amount", "value"].iloc[0])

        col1.metric("销售件数", total_sales_qty)
        col2.metric("退货件数", total_return_qty)
        col3.metric("净销售结算金额", f"{net_sales_amount:,.2f} ₽")
        col4.metric("平台最终应付金额", f"{final_payable_amount:,.2f} ₽")

        # 处理采购成本表（如果没上传，则成本视为 0）
        if cost_file is not None:
            try:
                cost_df = load_cost_table(cost_file)
            except Exception as e:
                st.error(f"读取采购成本文件时出错：{e}")
                cost_df = pd.DataFrame(columns=["SKU", "unit_cost"])
        else:
            st.warning("未上传采购成本文件，本次利润计算中的采购成本将视为 0。")
            cost_df = pd.DataFrame(columns=["SKU", "unit_cost"])

        # 计算利润表
        profit_by_sku = compute_profit_by_sku(
            net_sales_by_sku,
            sales_logistics_by_sku,
            cancel_logistics_by_sku,
            cost_df,
        )

        
        # 多个 tab 显示明细
        st.subheader("明细表")
        tabs = st.tabs([
            "1️⃣ 销售按SKU",
            "2️⃣ 退货按SKU",
            "3️⃣ 净销售按SKU",
            "4️⃣ 销售物流费用",
            "5️⃣ 取消订单物流",
            "6️⃣ SKU 取消率",
            "7️⃣ 费用汇总",
            "8️⃣ Final Overview",
            "9️⃣ 净利润按SKU",
        ])

        with tabs[0]:
            st.dataframe(sales_by_sku, use_container_width=True)

        with tabs[1]:
            st.dataframe(returns_by_sku, use_container_width=True)

        with tabs[2]:
            st.dataframe(net_sales_by_sku, use_container_width=True)

        with tabs[3]:
            st.dataframe(sales_logistics_by_sku, use_container_width=True)

        with tabs[4]:
            st.dataframe(cancel_logistics_by_sku, use_container_width=True)

        with tabs[5]:
            st.dataframe(cancellation_rate_by_sku, use_container_width=True)

        with tabs[6]:
            st.dataframe(fee_summary, use_container_width=True)

        with tabs[7]:
            st.dataframe(overview, use_container_width=True)
        with tabs[8]:
            st.dataframe(profit_by_sku, use_container_width=True)


        # 下载 summary.xlsx
        st.subheader("下载周报 Excel 总结")

        excel_bytes = build_summary_excel(
            week_label,
            sales_by_sku,
            returns_by_sku,
            net_sales_by_sku,
            sales_logistics_by_sku,
            cancel_logistics_by_sku,
            cancellation_rate_by_sku,
            fee_summary,
            overview,
            profit_by_sku,
        )

        st.download_button(
            label="📥 下载 summary.xlsx",
            data=excel_bytes,
            file_name=f"{week_label}_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
