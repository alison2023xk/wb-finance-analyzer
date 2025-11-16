import io
from pathlib import Path

import pandas as pd
import streamlit as st

# ==============================
# 0. 区域 & 联邦区 映射（来自 wb_region_stats）
# ==============================

# --- 区域 -> 联邦区 ---
REGION_TO_DISTRICT = {
    # Центральный федеральный округ
    "Москва": "Центральный",
    "Московская": "Центральный",
    "Белгородская": "Центральный",
    "Брянская": "Центральный",
    "Владимирская": "Центральный",
    "Воронежская": "Центральный",
    "Ивановская": "Центральный",
    "Калужская": "Центральный",
    "Костромская": "Центральный",
    "Курская": "Центральный",
    "Липецкая": "Центральный",
    "Орловская": "Центральный",
    "Рязанская": "Центральный",
    "Смоленская": "Центральный",
    "Тамбовская": "Центральный",
    "Тверская": "Центральный",
    "Тульская": "Центральный",
    "Ярославская": "Центральный",

    # Северо-Западный федеральный округ
    "Санкт-Петербург": "Северо-Западный",
    "Ленинградская": "Северо-Западный",
    "Калининградская": "Северо-Западный",
    "Мурманская": "Северо-Западный",
    "Архангельская": "Северо-Западный",
    "Вологодская": "Северо-Западный",
    "Новгородская": "Северо-Западный",
    "Псковская": "Северо-Западный",
    "Республика Карелия": "Северо-Западный",
    "Республика Коми": "Северо-Западный",

    # Южный федеральный округ
    "Краснодарский": "Южный",
    "Ростовская": "Южный",
    "Волгоградская": "Южный",
    "Астраханская": "Южный",
    "Республика Крым": "Южный",
    "Севастополь": "Южный",
    "Республика Калмыкия": "Южный",

    # Северо-Кавказский федеральный округ
    "Ставропольский": "Северо-Кавказский",
    "Кабардино-Балкарская": "Северо-Кавказский",
    "Республика Дагестан": "Северо-Кавказский",
    "Республика Ингушетия": "Северо-Кавказский",
    "Республика Северная Осетия": "Северо-Кавказский",
    "Чеченская": "Северо-Кавказский",
    "Карачаево-Черкесская": "Северо-Кавказский",

    # Приволжский федеральный округ
    "Республика Татарстан": "Приволжский",
    "Республика Башкортостан": "Приволжский",
    "Республика Мордовия": "Приволжский",
    "Республика Марий": "Приволжский",
    "Республика Марий Эл": "Приволжский",
    "Республика Чувашия": "Приволжский",
    "Нижегородская": "Приволжский",
    "Пензенская": "Приволжский",
    "Самарская": "Приволжский",
    "Саратовская": "Приволжский",
    "Ульяновская": "Приволжский",
    "Кировская": "Приволжский",
    "Оренбургская": "Приволжский",
    "Пермский": "Приволжский",

    # Уральский федеральный округ
    "Курганская": "Уральский",
    "Свердловская": "Уральский",
    "Тюменская": "Уральский",
    "Челябинская": "Уральский",
    "Ханты-Мансийский": "Уральский",
    "Ямало-Ненецкий": "Уральский",

    # Сибирский федеральный округ
    "Алтайский": "Сибирский",
    "Красноярский": "Сибирский",
    "Республика Бурятия": "Сибирский",
    "Республика Хакасия": "Сибирский",
    "Республика Тыва": "Сибирский",
    "Иркутская": "Сибирский",
    "Кемеровская": "Сибирский",
    "Омская": "Сибирский",
    "Новосибирская": "Сибирский",
    "Томская": "Сибирский",

    # Дальневосточный федеральный округ
    "Приморский": "Дальневосточный",
    "Хабаровский": "Дальневосточный",
    "Забайкальский": "Дальневосточный",
    "Сахалинская": "Дальневосточный",
    "Еврейская": "Дальневосточный",
    "Республика Саха": "Дальневосточный",
    "Республика Саха (Якутия)": "Дальневосточный",
    "Камчатский": "Дальневосточный",
    "Магаданская": "Дальневосточный",
    "Чукотский": "Дальневосточный",

    # 海外国家（非俄罗斯）
    "Минск": "Беларусь",
    "Минская": "Беларусь",
    "Брестская": "Беларусь",
    "Гродненская": "Беларусь",
    "Витебская": "Беларусь",
    "Могилёвская": "Беларусь",

    "Западно-Казахстанская": "Казахстан",
    "Северо-Казахстанская": "Казахстан",

    "Ереван": "Армения",

    # 默认兜底
    "Республика": "Другой регион РФ",
}

# 俄文区域名称 → 中文
REGION_CN = {
    "Москва": "莫斯科",
    "Московская": "莫斯科州",

    "Санкт-Петербург": "圣彼得堡",
    "Ленинградская": "列宁格勒州",

    "Краснодарский": "克拉斯诺达尔边疆区",
    "Ростовская": "罗斯托夫州",
    "Ставропольский": "斯塔夫罗波尔边疆区",

    "Нижегородская": "下诺夫哥罗德州",
    "Самарская": "萨马拉州",
    "Саратовская": "萨拉托夫州",
    "Оренбургская": "奥伦堡州",
    "Ульяновская": "乌里扬诺夫斯克州",
    "Кировская": "基洛夫州",
    "Пензенская": "彭扎州",
    "Чувашская": "楚瓦什共和国",

    "Свердловская": "斯维尔德洛夫斯克州",
    "Челябинская": "车里雅宾斯克州",
    "Курганская": "库尔干州",
    "Тюменская": "秋明州",
    "Ханты-Мансийский": "汉特-曼西自治区",
    "Ямало-Ненецкий": "亚马尔-涅涅茨自治区",

    "Приморский": "滨海边疆区",
    "Хабаровский": "哈巴罗夫斯克边疆区",
    "Забайкальский": "外贝加尔边疆区",
    "Сахалинская": "萨哈林州",
    "Еврейская": "犹太自治州",

    "Алтайский": "阿尔泰边疆区",
    "Красноярский": "克拉斯诺亚尔斯克边疆区",
    "Иркутская": "伊尔库茨克州",
    "Кемеровская": "克麦罗沃州",
    "Омская": "鄂木斯克州",
    "Новосибирская": "新西伯利亚州",
    "Томская": "托木斯克州",

    "Воронежская": "沃罗涅日州",
    "Белгородская": "别尔哥罗德州",
    "Смоленская": "斯摩棱斯克州",
    "Тверская": "特维尔州",
    "Брянская": "布良斯克州",
    "Орловская": "奥廖尔州",
    "Курская": "库尔斯克州",
    "Ивановская": "伊万诺沃州",
    "Калужская": "卡卢加州",
    "Костромская": "科斯特罗马州",
    "Липецкая": "利佩茨克州",
    "Тамбовская": "坦波夫州",
    "Ярославская": "雅罗斯拉夫尔州",
    "Владимирская": "弗拉基米尔州",
    "Рязанская": "梁赞州",

    "Мурманская": "穆尔曼斯克州",
    "Вологодская": "沃洛格达州",
    "Новгородская": "诺夫哥罗德州",
    "Псковская": "普斯科夫州",
    "Калининградская": "加里宁格勒州",

    "Севастополь": "塞瓦斯托波尔",

    # 白俄罗斯
    "Минск": "明斯克",
    "Минская": "明斯克州",
    "Гродненская": "格罗德诺州",
    "Брестская": "布列斯特州",
    "Витебская": "维捷布斯克州",
    "Могилёвская": "莫吉廖夫州",

    # 哈萨克斯坦
    "Западно-Казахстанская": "西哈萨克斯坦州",
    "Северо-Казахстанская": "北哈萨克斯坦州",

    # 亚美尼亚
    "Ереван": "埃里温",

    # 其他未知
    "Республика": "未知共和国",
}
REGION_CN.update({
    "Республика Крым": "克里米亚共和国",
    "Республика Башкортостан": "巴什科尔托斯坦共和国",
    "Республика Мордовия": "莫尔多瓦共和国",
    "Республика Марий": "马里埃尔共和国",
    "Республика Марий Эл": "马里埃尔共和国",
    "Республика Карелия": "卡累利阿共和国",
    "Республика Бурятия": "布里亚特共和国",
    "Республика Хакасия": "哈卡斯共和国",
    "Республика Ингушетия": "印古什共和国",
    "Республика Калмыкия": "卡尔梅克共和国",
    "Республика Саха": "萨哈共和国（雅库特）",
    "Республика Саха (Якутия)": "萨哈共和国（雅库特）",
    "Республика Тыва": "图瓦共和国",

    "Архангельская": "阿尔汉格尔斯克州",
    "Волгоградская": "伏尔加格勒州",
    "Астраханская": "阿斯特拉罕州",
    "Пермский": "彼尔姆边疆区",

    "Кабардино-Балкарская": "卡巴尔达-巴尔卡尔共和国",
    "Республика Дагестан": "达吉斯坦共和国",
    "Тульская": "图拉州",
    "Республика Адыгея": "阿迪格共和国",
    "Республика Татарстан": "鞑靼斯坦共和国",
})

# 联邦区中文映射
DISTRICT_CN = {
    "Центральный": "中央联邦区",
    "Северо-Западный": "西北联邦区",
    "Южный": "南部联邦区",
    "Северо-Кавказский": "北高加索联邦区",
    "Приволжский": "伏尔加联邦区",
    "Уральский": "乌拉尔联邦区",
    "Сибирский": "西伯利亚联邦区",
    "Дальневосточный": "远东联邦区",

    # 海外地区
    "Беларусь": "白俄罗斯",
    "Казахстан": "哈萨克斯坦",
    "Армения": "亚美尼亚",

    # 兜底分类
    "Другой регион РФ": "俄罗斯其他地区",
    "Прочие/СНГ": "其他独联体地区",
}


def map_district(region: str) -> str:
    """区域名 -> 联邦区 / 国家"""
    return REGION_TO_DISTRICT.get(region, "Прочие/СНГ")


def map_region_cn(region: str) -> str:
    return REGION_CN.get(region, region)


def map_district_cn(district: str) -> str:
    return DISTRICT_CN.get(district, district)


def get_address_column(df: pd.DataFrame) -> str:
    """
    找出地址列：
    优先使用“Наименование офиса доставки”
    """
    candidates = [
        "Наименование офиса доставки",
        "Наименование офиса",
    ]

    for col in df.columns:
        if col in candidates:
            return col
        if isinstance(col, str) and "офиса доставки" in col:
            return col

    # 找不到就抛错（方便你以后调整）
    raise RuntimeError("找不到地址列，请确认列名中包含 'Наименование офиса доставки' 等字段。")


def extract_region(address) -> str:
    """
    从地址里抽取区域名：
    - 如果是 Республика Татарстан → 返回 'Республика Татарстан'
    - 否则返回第一个单词，例如 'Московская область...' → 'Московская'
    """
    if not isinstance(address, str):
        return "未知地区"
    parts = address.split()
    if len(parts) >= 2 and parts[0] == "Республика":
        return " ".join(parts[:2])
    return parts[0]


def build_sales_table(df: pd.DataFrame, addr_col: str) -> pd.DataFrame:
    """
    销售成功表（按行统计）：
    条件：logistics_fee_type == 'К клиенту при продаже'
    """
    logistic_col = "logistics_fee_type"

    if logistic_col not in df.columns:
        raise RuntimeError("数据中缺少 'logistics_fee_type' 列，无法统计区域销售。")

    sales_df = df[df[logistic_col] == "К клиенту при продаже"].copy()

    if sales_df.empty:
        return pd.DataFrame(columns=["region", "sales"])

    sales_df["region"] = sales_df[addr_col].apply(extract_region)

    grouped = (
        sales_df.groupby("region")
        .agg(sales=("region", "count"))
        .reset_index()
        .sort_values("sales", ascending=False)
    )
    return grouped


def build_cancel_table(df: pd.DataFrame, addr_col: str) -> pd.DataFrame:
    """
    取消订单表（按行统计）：
    条件：logistics_fee_type == 'От клиента при отмене'
    """
    logistic_col = "logistics_fee_type"

    if logistic_col not in df.columns:
        raise RuntimeError("数据中缺少 'logistics_fee_type' 列，无法统计区域取消。")

    cancel_df = df[df[logistic_col] == "От клиента при отмене"].copy()

    if cancel_df.empty:
        return pd.DataFrame(columns=["region", "cancel_orders"])

    cancel_df["region"] = cancel_df[addr_col].apply(extract_region)

    grouped = (
        cancel_df.groupby("region")
        .agg(cancel_orders=("region", "count"))
        .reset_index()
        .sort_values("cancel_orders", ascending=False)
    )
    return grouped


def compute_region_tables(df: pd.DataFrame):
    """
    基于当前合并后的 df，计算：
    - sales_by_region：各区域销售笔数
    - cancel_by_region：各区域取消笔数
    - district_summary：各联邦区销售/取消/取消率
    """
    try:
        addr_col = get_address_column(df)
    except Exception:
        # 如果找不到地址列，返回空表，但不影响主流程
        empty_region = pd.DataFrame(columns=["region", "sales", "region_cn", "district", "district_cn"])
        empty_cancel = pd.DataFrame(columns=["region", "cancel_orders", "region_cn", "district", "district_cn"])
        empty_dist = pd.DataFrame(columns=["district", "district_cn", "sales", "cancel_orders", "total_orders", "cancel_rate"])
        return empty_region, empty_cancel, empty_dist

    sales_raw = build_sales_table(df, addr_col)      # region, sales
    cancel_raw = build_cancel_table(df, addr_col)    # region, cancel_orders

    # 补充中文 & 联邦区
    def enrich_region_table(base: pd.DataFrame, is_sales: bool) -> pd.DataFrame:
        if base.empty:
            cols = ["region"] + (["sales"] if is_sales else ["cancel_orders"])
            out = pd.DataFrame(columns=cols + ["region_cn", "district", "district_cn"])
            return out

        out = base.copy()
        out["region_cn"] = out["region"].apply(map_region_cn)
        out["district"] = out["region"].apply(map_district)
        out["district_cn"] = out["district"].apply(map_district_cn)
        return out

    sales_by_region = enrich_region_table(sales_raw, is_sales=True)
    cancel_by_region = enrich_region_table(cancel_raw, is_sales=False)

    # 按联邦区聚合
    if sales_by_region.empty and cancel_by_region.empty:
        district_summary = pd.DataFrame(
            columns=["district", "district_cn", "sales", "cancel_orders", "total_orders", "cancel_rate"]
        )
    else:
        sales_d = (
            sales_by_region.groupby("district", as_index=False)["sales"].sum()
            if not sales_by_region.empty
            else pd.DataFrame(columns=["district", "sales"])
        )
        cancel_d = (
            cancel_by_region.groupby("district", as_index=False)["cancel_orders"].sum()
            if not cancel_by_region.empty
            else pd.DataFrame(columns=["district", "cancel_orders"])
        )
        district_summary = pd.merge(sales_d, cancel_d, on="district", how="outer").fillna(0)
        district_summary["sales"] = district_summary["sales"].astype(int)
        district_summary["cancel_orders"] = district_summary["cancel_orders"].astype(int)
        district_summary["total_orders"] = district_summary["sales"] + district_summary["cancel_orders"]
        district_summary["cancel_rate"] = 0.0
        mask = district_summary["total_orders"] > 0
        district_summary.loc[mask, "cancel_rate"] = (
            district_summary.loc[mask, "cancel_orders"] / district_summary.loc[mask, "total_orders"]
        )
        district_summary["district_cn"] = district_summary["district"].apply(map_district_cn)
        district_summary = district_summary.sort_values("sales", ascending=False)

    return sales_by_region, cancel_by_region, district_summary


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
# 2. 读 & 合并上传的报表
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
# 3. 采购成本 & 利润
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

    # 同一个 SKU 如果出现多次，取平均
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

    # 3) 合并取消/退货相关的物流费用
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

    profit_df = profit_df.sort_values("SKU")

    return profit_df


# ==============================
# 4. 销售 / 退货 / 净销售
# ==============================

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

    net_df = net_df.sort_values("SKU")

    return net_df


# ==============================
# 5. 销售物流 / 取消物流 / 取消率
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
# 6. 费用汇总 & 总览
# ==============================

def compute_fee_summary(df: pd.DataFrame,
                        profit_by_sku: pd.DataFrame) -> pd.DataFrame:
    """
    费用汇总表：
      只保留两列：description / total_fee
      行包括：
        - 各费用类别（物流、罚款、忠诚计划等）
        - 采购成本
        - 平台其他费用合计
        - 总费用（平台费用 + 采购成本）
    """
    rows = []

    # 1) 各费用类别（不包含采购成本）
    platform_fee_total = 0.0
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
        platform_fee_total += total_fee

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

    # 3) 平台其他费用合计
    rows.append({
        "description": "平台其他费用合计",
        "total_fee": platform_fee_total,
    })

    # 4) 总费用 = 平台费用 + 采购成本
    total_all = platform_fee_total + purchase_total
    rows.append({
        "description": "总费用",
        "total_fee": total_all,
    })

    fee_df = pd.DataFrame(rows, columns=["description", "total_fee"])

    return fee_df


def compute_final_overview(df: pd.DataFrame,
                           fee_summary: pd.DataFrame) -> pd.DataFrame:
    sales_df = df[df["reason_for_payment"].isin(REASON_SALES)]
    returns_df = df[df["reason_for_payment"].isin(REASON_RETURNS)]

    total_sales_qty = len(sales_df)
    total_return_qty = len(returns_df)

    total_sales_amount = sales_df["amount_payable_goods"].sum()
    total_return_amount = returns_df["amount_payable_goods"].sum()

    net_sales_amount = total_sales_amount - total_return_amount

    # 从 fee_summary 中读出：平台费用 & 采购成本 & 总费用
    def get_fee(desc: str) -> float:
        mask = fee_summary["description"] == desc
        if mask.any():
            return float(fee_summary.loc[mask, "total_fee"].iloc[0])
        return 0.0

    platform_fee_amount = get_fee("平台其他费用合计")
    purchase_cost_total = get_fee("采购成本")
    total_fee_amount = get_fee("总费用")

    # 平台最终应付金额 = 净销售结算金额 - 平台费用（不扣采购成本）
    final_payable_amount = net_sales_amount - platform_fee_amount

    # 净利润 = 平台最终应付金额 - 采购成本
    net_profit = final_payable_amount - purchase_cost_total

    overview = pd.DataFrame(
        [
            {"metric": "total_sales_qty", "value": total_sales_qty},
            {"metric": "total_return_qty", "value": total_return_qty},
            {"metric": "total_sales_amount", "value": total_sales_amount},
            {"metric": "total_return_amount", "value": total_return_amount},
            {"metric": "net_sales_amount", "value": net_sales_amount},
            {"metric": "platform_fee_amount", "value": platform_fee_amount},
            {"metric": "purchase_cost_total", "value": purchase_cost_total},
            {"metric": "total_fee_amount", "value": total_fee_amount},
            {"metric": "final_payable_amount", "value": final_payable_amount},
            {"metric": "net_profit", "value": net_profit},
        ]
    )

    # 英文指标 -> 中文名称
    metric_zh_map = {
        "total_sales_qty": "销售件数",
        "total_return_qty": "退货件数",
        "total_sales_amount": "销售结算金额（含退货前）",
        "total_return_amount": "退货结算金额",
        "net_sales_amount": "净销售结算金额",
        "platform_fee_amount": "平台费用（不含采购成本）",
        "purchase_cost_total": "采购成本总额",
        "total_fee_amount": "总费用（平台费用+采购成本）",
        "final_payable_amount": "平台最终应付金额",
        "net_profit": "净利润",
    }

    overview["metric_zh"] = overview["metric"].map(metric_zh_map)

    # 调整列顺序：中文放前面
    overview = overview[["metric_zh", "metric", "value"]]

    return overview


# ==============================
# 7. 生成 summary.xlsx 供下载
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
                        profit_by_sku: pd.DataFrame,
                        sales_by_region: pd.DataFrame,
                        cancel_by_region: pd.DataFrame,
                        district_summary: pd.DataFrame) -> bytes:

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
        sales_by_region.to_excel(writer, sheet_name="Sales_by_Region", index=False)
        cancel_by_region.to_excel(writer, sheet_name="Cancel_by_Region", index=False)
        district_summary.to_excel(writer, sheet_name="District_Summary", index=False)

    output.seek(0)
    return output.getvalue()


# ==============================
# 8. Streamlit 网页界面
# ==============================

def main():
    st.set_page_config(page_title="WB 每周财务报表分析", layout="wide")

    st.title("WB 每周财务报表自动汇总（可视化版）")

    st.markdown(
        """
        使用说明：
        1. 在下方上传要分析的 WB 财务报表（可以一次上传多周、多份，境内 + 境外混合）；
        2. 输入本次分析的标签（例如：`20251103-1109` 或 `Q4汇总`）；
        3. 如需计算利润，请上传采购成本文件（SKU / 采购成本）；
        4. 点击“开始分析”，稍等即可查看结果，并在页面底部下载 summary.xlsx。
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

        # 区域统计（按地区 & 联邦区）
        sales_by_region, cancel_by_region, district_summary = compute_region_tables(df)

        # 处理采购成本表
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

        # 费用汇总 & 总览
        fee_summary = compute_fee_summary(df, profit_by_sku)
        overview = compute_final_overview(df, fee_summary)

        # 顶部总览指标
        st.subheader("本次分析关键指标总览")
        col1, col2, col3, col4 = st.columns(4)
        total_sales_qty = int(overview.loc[overview["metric"] == "total_sales_qty", "value"].iloc[0])
        total_return_qty = int(overview.loc[overview["metric"] == "total_return_qty", "value"].iloc[0])
        net_sales_amount = float(overview.loc[overview["metric"] == "net_sales_amount", "value"].iloc[0])
        final_payable_amount = float(overview.loc[overview["metric"] == "final_payable_amount", "value"].iloc[0])

        col1.metric("销售件数", total_sales_qty)
        col2.metric("退货件数", total_return_qty)
        col3.metric("净销售结算金额", f"{net_sales_amount:,.2f} ₽")
        col4.metric("平台最终应付金额", f"{final_payable_amount:,.2f} ₽")

        # 多个 tab 显示明细
        st.subheader("明细表")
        tabs = st.tabs([
            "1️⃣ 销售 & 退货 & 净销售",
            "2️⃣ 物流 & 取消率",
            "3️⃣ 费用 & 总览 & 利润",
            "4️⃣ 销售区域统计",
        ])

        # ====== Tab 1：销售 + 退货 + 净销售 ======
        with tabs[0]:
            st.markdown("### 净销售按 SKU")
            st.dataframe(net_sales_by_sku, use_container_width=True)

            st.markdown("---")
            left, right = st.columns(2)
            with left:
                st.markdown("#### 销售按 SKU")
                st.dataframe(sales_by_sku, use_container_width=True)
            with right:
                st.markdown("#### 退货按 SKU")
                st.dataframe(returns_by_sku, use_container_width=True)

        # ====== Tab 2：物流 + 取消率 ======
        with tabs[1]:
            st.markdown("### SKU 取消率")
            st.dataframe(cancellation_rate_by_sku, use_container_width=True)

            st.markdown("---")
            left, right = st.columns(2)
            with left:
                st.markdown("#### 销售物流费用")
                st.dataframe(sales_logistics_by_sku, use_container_width=True)
            with right:
                st.markdown("#### 取消订单物流费用")
                st.dataframe(cancel_logistics_by_sku, use_container_width=True)

        # ====== Tab 3：费用 + 总览 + 利润 ======
        with tabs[2]:
            st.markdown("### 总览（中文）")
            overview_display = overview[["metric_zh", "value"]].rename(
                columns={"metric_zh": "指标", "value": "数值"}
            )
            st.dataframe(overview_display, use_container_width=True)

            st.markdown("---")
            st.markdown("### 费用汇总")
            st.dataframe(fee_summary, use_container_width=True)

            st.markdown("---")
            st.markdown("### 净利润按 SKU")
            st.dataframe(profit_by_sku, use_container_width=True)

        # ====== Tab 4：区域统计 ======
        with tabs[3]:
            st.markdown("#### 按地区统计（Region）")
            st.dataframe(sales_by_region, use_container_width=True)
            st.markdown("#### 按地区取消（Region）")
            st.dataframe(cancel_by_region, use_container_width=True)
            st.markdown("#### 按联邦区统计汇总（District）")
            st.dataframe(district_summary, use_container_width=True)

        # 下载 summary.xlsx
        st.subheader("下载本次分析 Excel 总结")

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
            sales_by_region,
            cancel_by_region,
            district_summary,
        )

        st.download_button(
            label="📥 下载 summary.xlsx",
            data=excel_bytes,
            file_name=f"{week_label}_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()

