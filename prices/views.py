from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib import messages
from django.utils import timezone

from .models import *
from .forms import Price_input, dataImportForm
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from scipy.stats.mstats import gmean
import pandas as pd, numpy as np
import itertools, json


GROUP_NAMES = {
        'Food': "Озиқ-овқат маҳсулотлари",
        'Non-food': "Ноозиқ-овқат маҳсулотлар",
        'Service': "Хизматлар"
    }

CONTENT_TYPE_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class TemplateIterator(itertools.count):
    def next(self):
        return next(self)


def add_style(table):
    s = table.index('<thead>')
    f = table.index('</thead>')
    changing = table[s:f].replace('<th>', '<th><span>').replace('</th>', '</span></th>')
    table = table[:s] + changing + table[f:]
    table = table.replace('dataframe', 'table table-bordered table-striped changes')
    table = table.replace('text-align: right;', 'text-align: center;')
    # table = table.replace('<td>', '<td onclick="alert(\'hi!\')">')
    return table


def get_market_weights(region_names, good_names):
    names = ["good_id__name", "region_id__name", "weight"]
    mar_weig_df = pd.DataFrame(MarketWeight.objects.values(*names))
    mar_weig_df.columns = ["good", "region", "weight"]

    mar_weig_df["region"] = mar_weig_df["region"].astype("category")
    mar_weig_df["region"].cat.set_categories(region_names, inplace=True)
    mar_weig_df["good"] = mar_weig_df["good"].astype("category")
    mar_weig_df["good"].cat.set_categories(good_names, inplace=True)

    market_weights = pd.pivot_table(mar_weig_df, index=["good"], columns=["region"], values=["weight"])
    return market_weights['weight']


def create_table_df(sana):
    names = ["good_id__name", "region_id__name", "market_id__name", "price", "sunday", "market_id__is_market"]
    prices_tb = Price.objects.filter(sunday=sana).values(*names)
    df = pd.DataFrame(prices_tb).dropna(subset=["price"])
    df.columns = ["good", "region", "market", "price", "sunday", "is_market"]
    regions = pd.DataFrame(Region.objects.all().values()).set_index('id')
    goods = pd.DataFrame(Good.objects.filter(visible=True).values())

    df["region"] = df["region"].astype("category")
    df["region"].cat.set_categories(regions["name"], inplace=True)
    df["good"] = df["good"].astype("category")
    df["good"].cat.set_categories(goods["name"], inplace=True)

    pt = pd.pivot_table(df, index=["good"], columns=["is_market", "region"], values=["price"], aggfunc=np.mean)
    prices = pt['price']
    filler = pd.DataFrame(index=pt.index, columns=prices.columns.get_level_values(1))
    market = prices.get(True, filler)
    supermarket = prices.get(False, filler).fillna(0)

    market_weights = get_market_weights(regions["name"], goods["name"])

    nonexisting_goods = [x for x in market_weights.index if x not in pt.index]
    if nonexisting_goods:
        market_weights.drop(nonexisting_goods, inplace=True)

    market_weights[supermarket == 0] = 1
    avrg_market = market.mul(market_weights, fill_value=0)
    avrg_supermarket = supermarket.mul(1-market_weights, fill_value=0).fillna(0)
    pt = avrg_market + avrg_supermarket
    only_vals = np.nan_to_num(pt.values)

    table_df = pd.DataFrame(only_vals, list(pt.index), list(pt.columns))
    region_weights = np.array(regions['population']/sum(regions['population']))
    table_df["Республика"] = np.dot(only_vals, region_weights)
    table_df = table_df[["Республика", *regions['name']]]
    return table_df


def sundays_list():
    sundays = sorted(set(Price.objects.values_list('sunday', flat=True)), reverse=True)
    return [(x.strftime('%Y-%m-%d'), x.strftime('%d-%m-%Y')) for x in sundays]

def keep_prices(x, is_old=False):
    only_prices = defaultdict(dict)
    r = defaultdict(lambda: defaultdict(list))
    for item in x:
        good = item['good_id']
        price = item['price']
        only_prices[good][item['market_id']] = price
        r[good][int(item['market_id__is_market'])].append(price) 
    
    if is_old:
        goods = Good.objects.filter(active=True).values_list('id', flat=True)
        for i in goods:
            if 0 not in r[i]:
                r[i][0] = []
            if 1 not in r[i]:
                r[i][1] = []
    return json.dumps(only_prices), json.dumps(r)


@login_required(login_url='login')
def index(request):
    if not request.user.is_staff:
        goods = Good.objects.filter(visible=True, active=True)
        regionId = request.user.profile.region_id
        markets = Market.objects.filter(region_id=regionId)
        market_weights = MarketWeight.objects.filter(region_id=regionId).values('good_id','weight')
        weights = { x['good_id']:x['weight'] for x in market_weights }
        is_market = { x['id']:int(x['is_market']) for x in markets.values() }
        market_indices = {}
        y = 0
        for m in markets.values():
            if (not m['is_market']) and y != 1:
                y = 0
            market_indices[m['id']] = y
            y = y + 1

        sana = SetDate.objects.get(id=1)
        sunday = to_sunday().date() if sana.show_default else sana.date

        sundays = sorted(set(Price.objects.values_list('sunday', flat=True)), reverse=True)
        if sunday in sundays:
            ind = sundays.index(sunday)
            old_sunday = sundays[ind + 1]
        else:
            old_sunday = sundays[0]

        region = Region.objects.get(id=regionId).name
        value_list = ['price','good_id','market_id','market_id__is_market']
        cur_prices = list(Price.objects.filter(region=regionId, sunday=sunday).values(*value_list))
        old_prices = list(Price.objects.filter(region=regionId, sunday=old_sunday).values(*value_list))
        only_prices, latter_prices = keep_prices(cur_prices, True)
        old_prices, former_prices = keep_prices(old_prices)

        context = {
            'goods':goods, 
            'markets':markets, 
            'region':region,
            'regionId':regionId,
            'sunday':sunday.strftime('%d-%m-%Y'),
            'my_form':Price_input(),
            'curr_prices':only_prices,
            'old_prices':old_prices,
            'former_prices':former_prices,
            'latter_prices':latter_prices,
            'weights':json.dumps(weights),
            'is_market':json.dumps(is_market),
            'market_indices':json.dumps(market_indices),
            'iterator':TemplateIterator(),
            'goods_len':len(goods),
            }
        return render(request, 'index.html', context)
    
    else:
        sundays = sundays_list()
        sunday = sundays[0][0]
        table_df = create_table_df(sunday)
        table = add_style(table_df.astype(int).to_html())
        context = {
            'data':table,
            'sana':sundays,
            'sunday':sunday
            }
        return render(request, 'results.html', context)


@login_required(login_url='login')
def save_price(request):
    if request.method == "POST":
        user = request.user
        req = request.POST
        price = req.get('price')
        time = req.get('time')
        if time is None:
            time = timezone.now()
        else:
            time = datetime.fromtimestamp(float(time))

        try:
            existing = dict(
                # region_id=user.profile.region_id,
                region_id=req.get('regionId'),
                good_id=req.get('goodId'),
                market_id=req.get('marketId'),
                sunday=timezone.datetime.strptime(req.get('sunday'), '%d-%m-%Y').date()
                )
            data = {
                'price': int(price) if price else None,
                'author_id': user.id,
                'time': time,
                }

            if price:
                Price.objects.update_or_create(**existing, defaults=data)
            else:
                Price.objects.filter(**existing).delete()
        
            return HttpResponse('')

        except Exception as err:
            print(err, flush=True)
            return HttpResponse(status=500)



@staff_member_required
def change_date(request):
    new_date = request.GET.get('date')
    table_df = create_table_df(new_date)
    table = add_style(table_df.astype(int).to_html())
    return HttpResponse(table)


def changes_table(former, latter):
    names = ["good_id__name", "region_id__name", "market_id__name", "price", 
            "sunday", "market_id__is_market", "good_id__group"]
    data = Price.objects.filter(sunday__in=[former,latter]).values(*names)
    df = pd.DataFrame(data).dropna(subset=["price"])
    df.columns = ["good", "region", "market", "price", "sunday", "is_market", "group"]

    regions = pd.DataFrame(Region.objects.all().values()).set_index('id')
    goods = pd.DataFrame(Good.objects.all().values()).set_index('name')
    df["region"] = df["region"].astype("category")
    df["region"].cat.set_categories(regions['name'], inplace=True)
    df["good"] = df["good"].astype("category")
    df["good"].cat.set_categories(goods.index, inplace=True)

    indices = ["sunday", "group", "good"]
    labels = ["is_market", "region"]

    former_dt = datetime.strptime(former, '%Y-%m-%d').date()
    latter_dt = datetime.strptime(latter, '%Y-%m-%d').date()

    df_nd = df.drop_duplicates(['good','sunday'], keep='last')
    goods_former = set(df_nd[df_nd['sunday']==former_dt]['good'])
    goods_latter = set(df_nd[df_nd['sunday']==latter_dt]['good'])
    goods_names = set(goods.index)
    union = goods_former | goods_latter | goods_names
    intersection = goods_former & goods_latter & goods_names
    # symmetric difference of 3 sets
    nonexisting_goods = union - intersection
    df = df.drop(df.index[df['good'].isin(nonexisting_goods)])
    
    pt = pd.pivot_table(df, index=indices, columns=labels, values=["price"], aggfunc=gmean)
    ptc = pd.pivot_table(df, index=indices, columns="region", values=["price"], aggfunc='count')
    
    market_former = pt.loc[former_dt, ('price', True)].fillna(0)
    supermarket_former = pt.loc[former_dt, ('price', False)].fillna(0)
    market_latter = pt.loc[latter_dt, ('price', True)].fillna(0)
    supermarket_latter = pt.loc[latter_dt, ('price', False)].fillna(0)
    count_former = ptc.loc[former_dt, 'price'].fillna(0)
    count_latter = ptc.loc[latter_dt, 'price'].fillna(0)

    market_weights = get_market_weights(regions["name"], goods.index)
    cur_goods = market_latter.index.get_level_values(1)
    # nonexisting_goods = [x for x in market_weights.index if x not in cur_goods] 
    if nonexisting_goods:
        market_weights.drop(nonexisting_goods, inplace=True)
        goods.drop(nonexisting_goods, inplace=True)
        # market_former.drop(nonexisting_goods, level=1, inplace=True)
    
    count_diff = count_latter - count_former
    market_weights[supermarket_latter == 0] = 1
    market_div = market_latter.div(market_former, fill_value=0)
    change_market = (market_div**(market_weights)).replace(np.inf, 1)
    sm_div = supermarket_latter.div(supermarket_former, fill_value=0)
    change_sm = (sm_div**(1-market_weights)).replace(np.inf, 1)
    table_df = change_market.mul(change_sm)

    column_names = table_df.columns.tolist()
    groups = sorted(set(df[df['sunday']==latter_dt]['group']))
    df_subtotals = []
    df_counts = pd.DataFrame(np.zeros((1,14)), ["Умумий индекс"], column_names)
    total = np.zeros((1, 14))
    
    for gr in groups:
        good_weights = np.array(goods[goods['group']==gr]['weight'])
        current_gr = table_df.loc[gr]
        count_curr = count_diff.loc[gr]
        gr_name = pd.DataFrame(np.zeros((1,14)), [GROUP_NAMES[gr]], column_names)
        subtotal = np.dot(good_weights, current_gr).reshape((1,14))/sum(good_weights)
        df_subtotals.append(pd.DataFrame(subtotal, [GROUP_NAMES[gr]], column_names))
        df_subtotals.append(current_gr)
        df_counts = pd.concat([df_counts, gr_name, count_curr])
        total = np.add(total, subtotal * sum(good_weights))

    total /= sum(goods['weight'])
    df_total = pd.DataFrame(total, ["Умумий индекс"], column_names)

    table_df = pd.concat([df_total, *df_subtotals])

    region_weights = np.array(regions['population']/sum(regions['population']))
    table_df["Республика"] = (table_df ** region_weights).apply(np.prod, axis=1)
    df_counts["Республика"] = [0] * len(table_df)
    table_df = table_df[["Республика", *regions['name']]]
    df_counts = df_counts[["Республика", *regions['name']]]
    table_df = (table_df-1)*100

    return (table_df, df_counts)


def table_by_regions(sana, region=0):
    names = ["good_id__name", "region_id__name", "market_id__name", "price", "sunday", "market_id__market_order"]
    regions = pd.DataFrame(Region.objects.all().values()).set_index('id')
    goods = pd.DataFrame(Good.objects.filter(visible=True).values())
    col_names = ['Бозор1', 'Бозор2', 'Бозор3', 'Бозор4', 'Супермаркет1', 'Супермаркет2']

    params = {'sunday': sana}
    if region:
        params['region'] = region
        region_name = regions.loc[region]['name']
        col_names = Market.objects.filter(region=region).values_list('name', flat=True)

    values = Price.objects.filter(**params).values(*names)
    
    if values:
        df = pd.DataFrame(values).dropna(subset=["price"])
        df.columns = ["good", "region", "market", "price", "sunday", "Савдо объектлари"]

        df["region"] = df["region"].astype("category")
        df["region"].cat.set_categories(regions["name"], inplace=True)
        df["good"] = df["good"].astype("category")
        df["good"].cat.set_categories(goods["name"], inplace=True)

        pt = pd.pivot_table(df, index=["region", "good"], columns=["Савдо объектлари"], values=["price"])["price"]
        pt.rename_axis(index=["Ҳудудлар", "Товарлар"], inplace=True)
        pt = pt.fillna(0)
        orders = list(range(1,7))
        pt.rename(columns=dict(zip(orders, col_names)), inplace=True)

        return pt.loc[region_name] if region else pt
    
    else:
        return pd.DataFrame({'Маълумот мавжуд эмас': [0]})


@staff_member_required
def by_regions(request):
    sundays = sundays_list()
    regions = Region.objects.all()
    sunday = sundays[0][0]
    table_df = table_by_regions(sunday)
    table = add_style(table_df.astype(int).to_html())
    context = {
        'sunday': sunday,
        'sana': sundays,
        'regions': regions,
        'table': table, 
    }
    return render(request, 'by_regions.html', context)


@staff_member_required
def by_regions_update(request):
    date = request.GET.get('date')
    region = int(request.GET.get('region'))
    table_df = table_by_regions(date, region)
    table = add_style(table_df.astype(int).to_html())
    return HttpResponse(table)


# def conditional_html(table_df, df_counts):
#     is_matched = [row!=0 for col in df_counts.columns for row in df_counts[col]]
#     global i
#     i = 0
#     def nonmatch(x):
#         global i
#         cell_format = f'<span class="nonmatch" title="Савдо объектлари сони мос эмас">{x}</span>' if is_matched[i] else str(x)
#         i += 1
#         return cell_format
        
#     table = np.round(table_df, 1).fillna(0)
#     table = add_style(table.to_html(formatters={col: nonmatch for col in table_df.columns}, escape=False))
#     return table

def add_events(table_df, df_counts):
    from bs4 import BeautifulSoup

    romans = ['', 'I', 'II', 'III']
    table = np.round(table_df, 1).fillna(0)
    table = add_style(table.to_html())
    is_matched = [col!=0 for row in df_counts.index for col in df_counts.loc[row]]
    good_objects = Good.objects.all().values('id', 'name', 'description','order')
    goods = {x['name']: {
        'id':x['id'], 
        'description':x['description'],
        'order':x['order']
        } for x in good_objects}
    soup_table = BeautifulSoup(table, 'lxml')
    thead = soup_table.find('th')
    thead["class"] = "freeze"
    thead.string = 'Товар номи'
    num_th = soup_table.new_tag('th', attrs={"class": "freeze"})
    num_th.string = '№'
    thead.insert_before(num_th)
    tbody = soup_table.find('tbody')
    n = 0
    r = 0
    for row in tbody.find_all('tr'):
        good_th = row.find('th')
        good = good_th.text
        good_id = goods.get(good, {}).get('id')
        good_order = soup_table.new_tag('th')
        if good_id:
            good_order.string = str(goods.get(good, {}).get('order'))
            good_th['title'] = goods.get(good, {}).get('description')
            for i, col in enumerate(row.find_all('td')):
                if i:
                    attributes = {"class": "detailed", "onclick": f"openDetails({good_id}, {i})"}
                    if is_matched[n]:
                        attributes["class"] = "detailed nonmatch"
                        attributes["title"] = "Савдо объектлари сони мос эмас"
                    new_tag = soup_table.new_tag("span", attrs=attributes)
                    col.string.wrap(new_tag)
                n += 1
        else:
            n += 15
            good_order.string = romans[r]
            row["class"] = "groups"
            r += 1
        good_th.insert_before(good_order)

    return str(soup_table)


@staff_member_required
def changes(request):
    sundays = sundays_list()
    weeks = [sundays[1][0], sundays[0][0]]
    table_df, df_counts = changes_table(*weeks)
    # table = conditional_html(table_df, df_counts)
    table = add_events(table_df, df_counts)
    # titles = ["Умумий индекс", *GROUP_NAMES.values()]
    # titles = ','.join(f'tr:contains({x})' for x in titles)

    context = {
        'tab': table,
        'sana': sundays,
        # 'titles': titles,
        'former': weeks[0],
        'latter': weeks[1],
        'iterateover': range(6),
        'my_form':Price_input(),
    }

    return render(request, 'changes.html', context)


@staff_member_required
def change_button(request):
    former = request.GET.get('former')
    latter = request.GET.get('latter')
    table_df, df_counts = changes_table(former, latter)
    # table = conditional_html(table_df, df_counts)
    table = add_events(table_df, df_counts)
    return HttpResponse(table)


@staff_member_required
def bulk_button(request, model_name):
    models = {
        'good': Good,
        'price': Price,
        'market_weight': MarketWeight
        }

    data_type = {
        'good': 'товар',
        'price': 'нарх',
        'market_weight': 'вазн'
        }

    field_names = {
        'good': 'order, name, weight, description, group',
        'price': 'market_id, region_id, good_id, price, sunday',
        'market_weight': 'good_id, region_id, weight'
        }

    model = models[model_name]
    
    if request.method == "POST":
        ex_file = request.FILES["xlsx_file"]
        try:
            df = pd.read_excel(ex_file)
            if model_name == 'price':
                userID = request.user.id
                model.objects.bulk_create([
                    model(**record, author_id=userID) for record in df.to_dict('records')
                ])
            else:
                model.objects.bulk_create([
                    model(**record) for record in df.to_dict('records')
                ])

            msg = f"{len(df)} та {data_type[model_name]} муваффақиятли юкланди!"
            messages.success(request, msg)
            return redirect('..')
        except Exception as err:
            msg = "Илтимос, файлни тўғри форматда юкланг! Error: "
            messages.error(request, f'{msg} {err}')
    
    context = {
        "form": dataImportForm(),
        "field_name": field_names[model_name]
        }
    return render(request, "import_form.html", context)


def make_workbook(df, sheet_name):
    bio = BytesIO()
    writer = pd.ExcelWriter(bio, engine='xlsxwriter')
    df.to_excel(writer, sheet_name=sheet_name)
    writer.save()
    bio.seek(0)
    workbook = bio.read()
    return workbook


@staff_member_required
def export_prices(request):
    sunday = request.POST.get('date')
    table_df = create_table_df(sunday)
    workbook = make_workbook(table_df, 'Prices')
    response = HttpResponse(workbook, content_type=CONTENT_TYPE_XLSX)
    response['Content-Disposition'] = f'attachment; filename="Prices {sunday}.xlsx"'
    return response


@staff_member_required
def export_changes(request):
    former = request.POST.get('former')
    latter = request.POST.get('latter')
    table_df = changes_table(former, latter)[0]
    workbook = make_workbook(table_df, 'Changes')
    response = HttpResponse(workbook, content_type=CONTENT_TYPE_XLSX)
    filename = f"Changes {latter} by {former}.xlsx"
    response['Content-Disposition'] = 'attachment; filename=' + filename
    return response


@staff_member_required
def export_by_region(request):
    sana = request.POST.get('sana')
    region = int(request.POST.get('region_id'))
    table_df = table_by_regions(sana, region)
    workbook = make_workbook(table_df, 'by_regions')
    response = HttpResponse(workbook, content_type=CONTENT_TYPE_XLSX)
    filename = f"By_regions{(region if region else '')}_{sana}.xlsx"
    response['Content-Disposition'] = 'attachment; filename=' + filename
    return response


@staff_member_required
def get_details(request):
    goodId = request.GET.get('goodId')
    regionId = request.GET.get('regionId')
    former = request.GET.get('former')
    latter = request.GET.get('latter')

    cur_prices = list(Price.objects.filter(good=goodId, region=regionId, sunday__in=[former,latter]).values())
    only_prices = defaultdict(dict)
    for item in cur_prices:
        if item['price']:
            only_prices[str(item['sunday'])][str(item['market_id'])] = item['price']
    
    markets = list(Market.objects.filter(region=regionId).values('id', 'name'))
    data = {
        'markets': markets, 
        'prices': only_prices,
        'region': Region.objects.get(id=regionId).name,
        'good': Good.objects.get(id=goodId).name
        }
    
    return JsonResponse(data)