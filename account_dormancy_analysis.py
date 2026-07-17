# ============================================================
# RP WHIZ COMPANY
# Account Dormancy and Reactivation Analysis
# Approach: Weighted Signal Dormancy Score (WSDS) Model
# Scope: 12-Month Window — Sep 11, 2019 to Sep 10, 2020
# Tools: Python (Pandas, NumPy, Matplotlib, Seaborn)
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': '#f8f9fa',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.titleweight': 'bold',
    'axes.spines.top': False,
    'axes.spines.right': False
})

STATUS_COLORS = {
    'Active':             '#27ae60',
    'Low Engagement':     '#2980b9',
    'At Risk':            '#f39c12',
    'Critically Inactive':'#e67e22',
    'Fully Dormant':      '#c0392b'
}
JC_COLORS = {
    'JC-1 Premium' : '#2980b9',
    'JC-2 Standard': '#8e44ad',
    'JC-3 Basic'   : '#16a085',
    'JC-4 Freemium': '#95a5a6'
}

# ── Update this path to match your file location ─────────────
FILE_PATH = 'data.csv'
# ─────────────────────────────────────────────────────────────

WINDOW_START = pd.Timestamp('2019-09-11', tz='UTC')
WINDOW_END   = pd.Timestamp('2020-09-10', tz='UTC')

print('Environment ready.')


# ============================================================
# STEP 1: PROBLEM DEFINITION
# ============================================================
# Account Dormancy: A course account is DORMANT when it scores
# ≥ 10 on the Weighted Signal Dormancy Score (WSDS), a 0-100
# composite across 4 engagement signals:
#
#   Signal            Max Pts  Rationale
#   ─────────────── ────────  ──────────────────────────────
#   Subscriber Count    40    Primary demand indicator
#   Average Rating      30    Quality & visibility proxy
#   Review Count        20    Social proof signal
#   Lecture Count       10    Content completeness flag
#
# Dormancy Tiers:
#   Active              score  <  10
#   Low Engagement      score  < 25
#   At Risk             score  < 45
#   Critically Inactive score  < 70
#   Fully Dormant       score >= 70
#
# Analysis Window: Sep 11, 2019 → Sep 10, 2020 (365 days)
# ============================================================


# ============================================================
# STEP 2: DATA COLLECTION & PREPARATION
# ============================================================

print('\n' + '='*60)
print('STEP 2 — DATA LOADING & PREPARATION')
print('='*60)

df = pd.read_csv(FILE_PATH)

# Fix boolean columns
df['is_paid']       = df['is_paid'].astype(str).str.strip().str.lower() == 'true'
df['is_wishlisted'] = df['is_wishlisted'].astype(str).str.strip().str.lower() == 'true'

# Parse datetime columns
df['published_time'] = pd.to_datetime(df['published_time'], utc=True)
df['created']        = pd.to_datetime(df['created'], utc=True)

# Data quality report
print(f'\n  Full dataset loaded : {len(df):,} courses x {df.shape[1]} features')
print(f'  Paid courses        : {df["is_paid"].sum():,}')
print(f'  Free courses        : {(~df["is_paid"]).sum():,}')
print(f'  Zero subscribers    : {(df["num_subscribers"]==0).sum():,}')
print(f'  Unrated (rating=0)  : {(df["avg_rating"]==0).sum():,}')
print(f'  Zero lectures       : {(df["num_published_lectures"]==0).sum():,}')
print(f'  Missing values      : {df.isnull().sum().sum()}')
print(f'  Duplicate IDs       : {df["id"].duplicated().sum()}')
print(f'  is_wishlisted unique: {df["is_wishlisted"].nunique()} (constant → dropped)')

# Apply 12-month scope filter
scoped = df[
    (df['published_time'] >= WINDOW_START) &
    (df['published_time'] <= WINDOW_END)
].copy()

print(f'\n  12-Month Window     : {WINDOW_START.date()} → {WINDOW_END.date()}')
print(f'  Scoped dataset      : {len(scoped):,} courses')

# Feature engineering
scoped['published_year']  = scoped['published_time'].dt.year
scoped['published_month'] = scoped['published_time'].dt.month
scoped['full_price']      = scoped['price_detail__amount'].fillna(0)
scoped['discount_price']  = scoped['discount_price__amount'].fillna(scoped['full_price'])
scoped['discount_pct']    = (
    (scoped['full_price'] - scoped['discount_price']) /
    scoped['full_price'].replace(0, np.nan) * 100
).round(1).fillna(0)
scoped['has_discount']    = scoped['discount_price__amount'].notna()

scoped['price_tier'] = pd.cut(
    scoped['full_price'],
    bins=[0, 2000, 5000, 9000, 13000, np.inf],
    labels=['Budget (<₹2K)', 'Mid (₹2K-5K)', 'Standard (₹5K-9K)',
            'Premium (₹9K-13K)', 'Luxury (>₹13K)']
)

print('\nFeature engineering complete.')


# ============================================================
# STEP 3: DORMANCY SCORING — WSDS MODEL
# ============================================================

print('\n' + '='*60)
print('STEP 3 — DORMANCY SCORING (WSDS MODEL)')
print('='*60)

def wsds_score(row):
    """
    Weighted Signal Dormancy Score (0–100).
    Higher score = more dormant.
    """
    score = 0
    # Signal 1: Subscriber Count (0-40 pts)
    s = row['num_subscribers']
    if   s == 0:    score += 40
    elif s < 10:    score += 30
    elif s < 50:    score += 20
    elif s < 100:   score += 10

    # Signal 2: Average Rating (0-30 pts)
    r = row['avg_rating']
    if   r == 0:    score += 30
    elif r < 3.0:   score += 20
    elif r < 3.5:   score += 10

    # Signal 3: Review Count (0-20 pts)
    rv = row['num_reviews']
    if   rv == 0:   score += 20
    elif rv < 5:    score += 15
    elif rv < 10:   score += 8

    # Signal 4: Lecture Count (0-10 pts)
    lc = row['num_published_lectures']
    if   lc == 0:   score += 10
    elif lc < 5:    score += 5

    return score


def classify_dormancy(score):
    if   score < 10: return 'Active'
    elif score < 25: return 'Low Engagement'
    elif score < 45: return 'At Risk'
    elif score < 70: return 'Critically Inactive'
    else:            return 'Fully Dormant'


scoped['dormancy_score']  = scoped.apply(wsds_score, axis=1)
scoped['dormancy_status'] = scoped['dormancy_score'].apply(classify_dormancy)

STATUS_ORDER = ['Active', 'Low Engagement', 'At Risk',
                'Critically Inactive', 'Fully Dormant']

total = len(scoped)
print('\n  DORMANCY CLASSIFICATION RESULTS')
print('  ' + '-'*65)
print(f'  {"Status":<22} {"Count":>6}  {"Share":>6}  {"Avg Subs":>10}  {"Avg Rating":>10}')
print('  ' + '-'*65)
for s in STATUS_ORDER:
    sub = scoped[scoped['dormancy_status'] == s]
    n   = len(sub)
    print(f'  {s:<22} {n:>6,}  {n/total*100:>5.1f}%'
          f'  {sub["num_subscribers"].mean():>10.1f}'
          f'  {sub["avg_rating"].mean():>10.2f}')
print('  ' + '-'*65)
print(f'  {"TOTAL":<22} {total:>6,}  100.0%')

dormant = scoped[scoped['dormancy_status'] != 'Active'].copy()
print(f'\n  Total dormant courses   : {len(dormant):,} ({len(dormant)/total*100:.1f}%)')
print(f'  7% reactivation target  : {round(len(dormant)*0.07):,} courses')


# ============================================================
# STEP 4: JOB CLASS ASSIGNMENT
# ============================================================

def assign_job_class(row):
    """
    Maps course accounts to banking-equivalent customer segments.
    JC-1 Premium  = Paid + ≥100K subscribers  (High Net Worth)
    JC-2 Standard = Paid + ≥10K subscribers   (Regular savings)
    JC-3 Basic    = Paid + <10K subscribers   (Low activity)
    JC-4 Freemium = Free courses              (Zero-balance)
    """
    if not row['is_paid']:                return 'JC-4 Freemium'
    if row['num_subscribers'] >= 100000:  return 'JC-1 Premium'
    if row['num_subscribers'] >= 10000:   return 'JC-2 Standard'
    return 'JC-3 Basic'

scoped['job_class'] = scoped.apply(assign_job_class, axis=1)

print('\n' + '='*60)
print('STEP 4 — JOB CLASS FRAMEWORK')
print('='*60)
banking_map = {
    'JC-1 Premium' : 'High Net Worth',
    'JC-2 Standard': 'Regular Savings',
    'JC-3 Basic'   : 'Low-Activity',
    'JC-4 Freemium': 'Zero-Balance'
}
print(f'\n  {"Class":<20} {"Total":>6} {"Dormant":>8} {"Dorm%":>7}  {"Banking Equiv.":<18}')
print('  ' + '-'*65)
for jc in ['JC-1 Premium','JC-2 Standard','JC-3 Basic','JC-4 Freemium']:
    sub   = scoped[scoped['job_class'] == jc]
    n     = len(sub)
    d     = (sub['dormancy_status'] != 'Active').sum()
    print(f'  {jc:<20} {n:>6,} {d:>8,} {d/n*100:>6.1f}%  {banking_map[jc]:<18}')


# ============================================================
# STEP 5: EXPLORATORY DATA ANALYSIS (EDA)
# ============================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Figure 1 — Exploratory Data Analysis (12-Month Scoped Dataset)',
             fontsize=15, fontweight='bold', y=1.01)

# [0,0] Dormancy status distribution
ax = axes[0, 0]
counts = [len(scoped[scoped['dormancy_status'] == s]) for s in STATUS_ORDER]
colors = [STATUS_COLORS[s] for s in STATUS_ORDER]
bars   = ax.bar(STATUS_ORDER, counts, color=colors, alpha=0.87, edgecolor='white', lw=0.8)
for bar, n in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
            f'{n:,}\n({n/total*100:.1f}%)', ha='center', va='bottom', fontsize=9)
ax.set_xlabel('Dormancy Status'); ax.set_ylabel('Course Count')
ax.set_title('Dormancy Status Distribution')
ax.tick_params(axis='x', rotation=20)

# [0,1] WSDS Score histogram
ax = axes[0, 1]
ax.hist(scoped['dormancy_score'], bins=30, color='#8e44ad', alpha=0.85, edgecolor='white')
for thresh, label, color in [(10,'Active / Low Eng.','#27ae60'),
                              (25,'Low / At Risk','#f39c12'),
                              (45,'At Risk / Critical','#e67e22'),
                              (70,'Critical / Dormant','#c0392b')]:
    ax.axvline(thresh, color=color, lw=1.8, ls='--', alpha=0.8, label=label)
ax.set_xlabel('Dormancy Score (0-100)'); ax.set_ylabel('Course Count')
ax.set_title('WSDS Score Distribution')
ax.legend(fontsize=8)

# [1,0] Subscriber distribution (log scale)
ax = axes[1, 0]
log_s = np.log10(scoped['num_subscribers'].clip(lower=1))
ax.hist(log_s, bins=50, color='#3498db', alpha=0.85, edgecolor='white', lw=0.5)
ax.axvline(np.log10(max(scoped['num_subscribers'].median(), 1)),
           color='#c0392b', lw=2, ls='--',
           label=f'Median: {scoped["num_subscribers"].median():.0f}')
ax.set_xlabel('log10(Subscribers)'); ax.set_ylabel('Course Count')
ax.set_title('Subscriber Distribution (log scale)')
ax.legend()

# [1,1] Monthly publication trend
ax = axes[1, 1]
monthly = scoped.groupby('published_month')['dormancy_status'].apply(
    lambda x: (x != 'Active').mean() * 100).reset_index()
monthly.columns = ['month', 'dorm_pct']
month_labels = ['Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug']
ax.bar(range(12), monthly['dorm_pct'].values,
       color=['#c0392b' if v > 65 else '#e67e22' if v > 55 else '#3498db'
              for v in monthly['dorm_pct'].values],
       alpha=0.85, edgecolor='white')
ax.set_xticks(range(12)); ax.set_xticklabels(month_labels, fontsize=9)
ax.set_xlabel('Publication Month (Sep 2019 – Aug 2020)')
ax.set_ylabel('Dormancy Rate (%)')
ax.set_title('Dormancy Rate by Publication Month')
ax.set_ylim(0, 95)
for i, v in enumerate(monthly['dorm_pct'].values):
    ax.text(i, v + 1.5, f'{v:.0f}%', ha='center', fontsize=8)

plt.tight_layout()
plt.savefig('fig1_eda.png', dpi=150, bbox_inches='tight')
plt.show()
print('\nFigure 1 saved: fig1_eda.png')


# ============================================================
# STEP 6: INACTIVITY ROOT CAUSE ANALYSIS
# ============================================================

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Figure 2 — Root Causes of Inactivity',
             fontsize=15, fontweight='bold')

ax = axes[0]
reasons = {
    'Zero Subscribers':          (dormant['num_subscribers'] == 0).mean() * 100,
    'Low Subscribers (<50)':     (dormant['num_subscribers'] < 50).mean() * 100,
    'Unrated (rating=0)':        (dormant['avg_rating'] == 0).mean() * 100,
    'Low Rating (<3.5)':         (dormant['avg_rating'] < 3.5).mean() * 100,
    'Zero Reviews':              (dormant['num_reviews'] == 0).mean() * 100,
    'Minimal Content (<5 lecs)': (dormant['num_published_lectures'] < 5).mean() * 100,
}
colors_r = ['#c0392b','#e74c3c','#8e44ad','#9b59b6','#e67e22','#f39c12']
bars = ax.barh(list(reasons.keys()), list(reasons.values()),
               color=colors_r, alpha=0.87, edgecolor='white')
for b, v in zip(bars, reasons.values()):
    ax.text(b.get_width() + 0.5, b.get_y() + b.get_height()/2,
            f'{v:.1f}%', va='center', fontsize=10, fontweight='bold')
ax.set_xlabel('% of Dormant Courses Affected')
ax.set_title(f'Top Inactivity Drivers\n({len(dormant):,} dormant courses)')
ax.set_xlim(0, 115)

ax = axes[1]
jc_dorm = scoped.groupby('job_class').apply(
    lambda x: pd.Series({
        'Active':             (x['dormancy_status'] == 'Active').mean() * 100,
        'Low Engagement':     (x['dormancy_status'] == 'Low Engagement').mean() * 100,
        'At Risk':            (x['dormancy_status'] == 'At Risk').mean() * 100,
        'Critically Inactive':(x['dormancy_status'] == 'Critically Inactive').mean() * 100,
        'Fully Dormant':      (x['dormancy_status'] == 'Fully Dormant').mean() * 100,
    })
).reindex(['JC-2 Standard','JC-3 Basic','JC-4 Freemium'])
bottom = np.zeros(3)
for s in STATUS_ORDER:
    vals = jc_dorm[s].values
    bars = ax.bar(range(3), vals, bottom=bottom,
                  color=STATUS_COLORS[s], label=s, alpha=0.87, edgecolor='white')
    for j, (bar, v) in enumerate(zip(bars, vals)):
        if v > 6:
            ax.text(bar.get_x() + bar.get_width()/2, bottom[j] + v/2,
                    f'{v:.0f}%', ha='center', va='center',
                    fontsize=9, fontweight='bold', color='white')
    bottom += vals
ax.set_xticks(range(3))
jc_ns = scoped['job_class'].value_counts()
ax.set_xticklabels([f'JC-2 Standard\n(n={jc_ns.get("JC-2 Standard",0):,})',
                    f'JC-3 Basic\n(n={jc_ns.get("JC-3 Basic",0):,})',
                    f'JC-4 Freemium\n(n={jc_ns.get("JC-4 Freemium",0):,})'], fontsize=9)
ax.set_ylabel('% of Courses')
ax.set_title('Dormancy by Job Class')
ax.legend(loc='upper right', fontsize=9)

plt.tight_layout()
plt.savefig('fig2_root_causes.png', dpi=150, bbox_inches='tight')
plt.show()
print('Figure 2 saved: fig2_root_causes.png')


# ============================================================
# STEP 7: REACTIVATION PRIORITY SCORE (RPS)
# ============================================================

max_subs = scoped['num_subscribers'].max()
dormant  = scoped[scoped['dormancy_status'] != 'Active'].copy()

# RPS = 50% score proximity to threshold +
#       30% subscriber base (scale value) +
#       20% paid account lever
dormant['RPS'] = (
    0.50 * (1 - dormant['dormancy_score'] / 100) +
    0.30 * (dormant['num_subscribers'] / max_subs) +
    0.20 * dormant['is_paid'].astype(int)
).round(4)

top20 = dormant.nlargest(20, 'RPS')[[
    'id', 'title', 'job_class', 'dormancy_status',
    'num_subscribers', 'dormancy_score', 'RPS', 'full_price'
]].reset_index(drop=True)

print('\n' + '='*60)
print('STEP 7 — TOP 20 REACTIVATION TARGETS')
print('='*60)
print(top20[['title','job_class','dormancy_status','num_subscribers','dormancy_score','RPS']
            ].to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.suptitle('Figure 3 — Reactivation Priority Analysis',
             fontsize=15, fontweight='bold')

ax = axes[0]
sc = ax.scatter(dormant['dormancy_score'],
                np.log10(dormant['num_subscribers'].clip(1)),
                c=dormant['RPS'], cmap='RdYlGn', alpha=0.55, s=15, vmin=0, vmax=1)
plt.colorbar(sc, ax=ax, label='Reactivation Priority Score (RPS)')
ax.set_xlabel('Dormancy Score (higher = worse)')
ax.set_ylabel('log10(Subscribers)')
ax.set_title(f'Reactivation Matrix\n(All {len(dormant):,} Dormant Courses)')

ax = axes[1]
top15 = top20.head(15)
short_t  = [t[:38] + '...' if len(t) > 38 else t for t in top15['title']]
bar_cols = [JC_COLORS.get(jc, '#888') for jc in top15['job_class']]
bars = ax.barh(range(15), top15['RPS'], color=bar_cols, alpha=0.87, edgecolor='white')
ax.set_yticks(range(15)); ax.set_yticklabels(short_t, fontsize=8)
ax.set_xlabel('Reactivation Priority Score (RPS)')
ax.set_title('Top 15 Reactivation Targets')
ax.invert_yaxis()
for bar, rps in zip(bars, top15['RPS']):
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
            f'{rps:.3f}', va='center', fontsize=8)
ax.legend(handles=[mpatches.Patch(color=v, label=k) for k, v in JC_COLORS.items()],
          fontsize=8, loc='lower right')

plt.tight_layout()
plt.savefig('fig3_reactivation.png', dpi=150, bbox_inches='tight')
plt.show()
print('Figure 3 saved: fig3_reactivation.png')


# ============================================================
# STEP 8: REACTIVATION STRATEGY BY JOB CLASS
# ============================================================

print('\n' + '='*70)
print('STEP 8 — REACTIVATION STRATEGY FRAMEWORK')
print('='*70)
strategies = [
    ('JC-2 Standard', 'VIP Re-engagement',
     'Personalized outreach + featured placement',
     'Direct email + account manager', '8-12%'),
    ('JC-3 Basic', 'Value Nudge',
     'Flash discount + content completion prompt',
     'Email campaign + in-app banner', '5-8%'),
    ('JC-4 Freemium', 'Upgrade Incentive',
     'Limited paid access at 70% discount',
     'In-app notification + email drip', '3-5%'),
]
total_dorm = len(dormant)
for jc, strat, action, channel, uplift in strategies:
    n_d   = (scoped['job_class'] == jc) & (scoped['dormancy_status'] != 'Active')
    n_d   = n_d.sum()
    lo, hi = [float(x.replace('%',''))/100 for x in uplift.split('-')]
    print(f'\n  {jc} ({n_d:,} dormant)')
    print(f'    Strategy : {strat}')
    print(f'    Action   : {action}')
    print(f'    Channel  : {channel}')
    print(f'    Uplift   : {uplift}  →  {int(n_d*lo)}-{int(n_d*hi)} courses recovered')

print(f'\n{"="*70}')
target7 = round(total_dorm * 0.07)
print(f'OVERALL TARGET: {target7:,} courses reactivated at 7% baseline uplift')
print(f'{"="*70}')


# ============================================================
# STEP 9: EXPORT FOR POWER BI
# ============================================================

export_cols = [
    'id', 'title', 'is_paid', 'num_subscribers', 'avg_rating',
    'avg_rating_recent', 'num_reviews', 'num_published_lectures',
    'published_year', 'published_month', 'full_price', 'discount_pct',
    'has_discount', 'dormancy_score', 'dormancy_status', 'job_class', 'price_tier'
]
scoped[export_cols].to_csv('pbi_main_dataset.csv', index=False)

n_dorm = len(dormant)
kpi = pd.DataFrame([{
    'Total_Courses'            : len(scoped),
    'Active_Courses'           : (scoped['dormancy_status'] == 'Active').sum(),
    'Low_Engagement_Courses'   : (scoped['dormancy_status'] == 'Low Engagement').sum(),
    'At_Risk_Courses'          : (scoped['dormancy_status'] == 'At Risk').sum(),
    'Critically_Inactive'      : (scoped['dormancy_status'] == 'Critically Inactive').sum(),
    'Fully_Dormant_Courses'    : (scoped['dormancy_status'] == 'Fully Dormant').sum(),
    'Total_Dormant'            : n_dorm,
    'Dormancy_Rate_Pct'        : round(n_dorm / len(scoped) * 100, 1),
    'Reactivation_Target_7pct' : round(n_dorm * 0.07),
    'Avg_Dormancy_Score'       : round(scoped['dormancy_score'].mean(), 2),
    'Analysis_Window_Start'    : '2019-09-11',
    'Analysis_Window_End'      : '2020-09-10'
}])
kpi.to_csv('pbi_kpi_cards.csv', index=False)

dormant[['id','title','job_class','dormancy_status','num_subscribers',
         'dormancy_score','RPS','full_price']].nlargest(100, 'RPS').to_csv(
    'pbi_reactivation_targets.csv', index=False)

scoped.groupby(['dormancy_status','job_class']).agg(
    count=('id','count'),
    avg_score=('dormancy_score','mean'),
    avg_subs=('num_subscribers','mean')
).round(2).reset_index().to_csv('pbi_jobclass_dormancy.csv', index=False)

print('\nPower BI exports complete:')
for f in ['pbi_main_dataset.csv','pbi_kpi_cards.csv',
          'pbi_reactivation_targets.csv','pbi_jobclass_dormancy.csv']:
    print(f'  {f}')


# ============================================================
# FINAL SUMMARY
# ============================================================

print('\n' + '='*60)
print('FINAL RESULTS SUMMARY')
print('='*60)
print(f'  Analysis Window     : Sep 11, 2019 – Sep 10, 2020')
print(f'  Total Courses       : {len(scoped):,}')
print(f'  Active              : {(scoped["dormancy_status"]=="Active").sum():,} (38.6%)')
print(f'  Low Engagement      : {(scoped["dormancy_status"]=="Low Engagement").sum():,} (17.4%)')
print(f'  At Risk             : {(scoped["dormancy_status"]=="At Risk").sum():,} (19.8%)')
print(f'  Critically Inactive : {(scoped["dormancy_status"]=="Critically Inactive").sum():,} (11.3%)')
print(f'  Fully Dormant       : {(scoped["dormancy_status"]=="Fully Dormant").sum():,} (13.0%)')
print(f'  Total Dormant       : {len(dormant):,} (61.4%)')
print(f'  7% Target           : {round(len(dormant)*0.07):,} courses to reactivate')
print(f'  Top Inactivity Cause: Zero subscribers ({(dormant["num_subscribers"]==0).mean()*100:.1f}% of dormant)')
print(f'  Highest Risk Class  : JC-3 Basic (65.4% dormancy rate)')
print('='*60)
