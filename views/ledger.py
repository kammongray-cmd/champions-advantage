import streamlit as st
import pandas as pd
from datetime import datetime, date
from calendar import monthrange
from services.database_manager import get_paid_commissions_for_ledger, get_all_projects_for_ledger, update_project_ledger
from services.email_service import send_commission_report_email
from services.timezone_utils import today_mountain, now_mountain


def get_pay_period_info(payment_date):
    """Determine pay period from payment date.
    Period 1: 1st-15th (paid on 20th, submission due 16th)
    Period 2: 16th-EOM (paid on 5th of next month, submission due 1st)
    """
    if isinstance(payment_date, str):
        payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
    
    day = payment_date.day
    if day <= 15:
        return 1, "1st - 15th", "Paid on the 20th", "Submission Due: 16th"
    else:
        return 2, "16th - End of Month", "Paid on the 5th", "Submission Due: 1st"


def get_deadline_alert():
    """Check if today is a submission deadline day (in Mountain Time)."""
    today = today_mountain()
    day = today.day
    month_name = today.strftime("%B %Y")
    
    if day == 16:
        return True, f"Period 1 Complete ({month_name}). Review and send commission report to Bruno today."
    elif day == 1:
        prev_month = (today.replace(day=1) - pd.Timedelta(days=1))
        prev_month_name = prev_month.strftime("%B %Y")
        return True, f"Period 2 Complete ({prev_month_name}). Review and send commission report to Bruno today."
    
    return False, ""


def get_current_period():
    """Get the current pay period (1 or 2) in Mountain Time."""
    return 1 if today_mountain().day <= 15 else 2


def get_report_period_info():
    """Get the period info for commission report generation.
    On deadline days (16th or 1st), returns the period that just closed.
    Otherwise returns the current period in progress.
    Uses Mountain Time for date calculations."""
    today = today_mountain()
    day = today.day
    
    if day == 16:
        year = today.year
        month = today.month
        period = 1
        date_range = f"{today.strftime('%B %Y')} 1st - 15th"
        start_day, end_day = 1, 15
    elif day == 1:
        prev_month = today.replace(day=1) - pd.Timedelta(days=1)
        year = prev_month.year
        month = prev_month.month
        period = 2
        last_day = monthrange(year, month)[1]
        date_range = f"{prev_month.strftime('%B %Y')} 16th - {last_day}th"
        start_day, end_day = 16, 31
    else:
        year = today.year
        month = today.month
        if today.day <= 15:
            period = 1
            date_range = f"{today.strftime('%B %Y')} 1st - 15th"
            start_day, end_day = 1, 15
        else:
            period = 2
            last_day = monthrange(year, month)[1]
            date_range = f"{today.strftime('%B %Y')} 16th - {last_day}th"
            start_day, end_day = 16, 31
    
    return year, month, period, date_range, start_day, end_day


def get_current_period_date_range():
    """Get the date range string for the report period."""
    _, _, _, date_range, _, _ = get_report_period_info()
    return date_range


def group_commissions_by_period(commissions):
    """Group commissions by Month and Pay Period."""
    grouped = {}
    
    for comm in commissions:
        payment_date = comm.get("payment_date")
        if not payment_date:
            continue
        
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
        
        year = payment_date.year
        month = payment_date.month
        month_name = payment_date.strftime("%B %Y")
        period_num, period_label, paid_on, submission_due = get_pay_period_info(payment_date)
        
        key = (year, month, period_num)
        if key not in grouped:
            grouped[key] = {
                "month_name": month_name,
                "period_num": period_num,
                "period_label": period_label,
                "paid_on": paid_on,
                "submission_due": submission_due,
                "year": year,
                "month": month,
                "commissions": []
            }
        
        grouped[key]["commissions"].append(comm)
    
    sorted_keys = sorted(grouped.keys(), reverse=True)
    return [(key, grouped[key]) for key in sorted_keys]


def get_report_period_commissions(commissions):
    """Filter commissions for the report period (adjusts for deadline days)."""
    year, month, period, date_range, start_day, end_day = get_report_period_info()
    
    filtered = []
    for comm in commissions:
        payment_date = comm.get("payment_date")
        if not payment_date:
            continue
        
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
        
        if (payment_date.year == year and 
            payment_date.month == month and
            start_day <= payment_date.day <= end_day):
            filtered.append(comm)
    
    return filtered


def render_ledger():
    """Render the Finance Ledger view showing only paid commissions grouped by pay period."""
    st.markdown('<h2 style="color: #E5E5E5;">Commission Ledger</h2>', unsafe_allow_html=True)
    
    has_alert, alert_message = get_deadline_alert()
    if has_alert:
        st.markdown(f"""
        <div style="
            background: linear-gradient(145deg, #FF6B35 0%, #D4380D 100%);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 20px;
            border: 2px solid #FF6B35;
        ">
            <p style="color: white; font-size: 16px; font-weight: 600; margin: 0;">
                {alert_message}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Paid Commissions", "All Projects (Edit Rates)"])
    
    with tab1:
        render_paid_commissions_tab()
    
    with tab2:
        render_all_projects_tab()


def render_paid_commissions_tab():
    """Render the paid commissions view grouped by pay period."""
    st.markdown(
        '<p style="color: #888; font-size: 14px;">Showing only projects with recorded payments. Grouped by month and pay period.</p>',
        unsafe_allow_html=True
    )
    
    commissions = get_paid_commissions_for_ledger()
    
    if not commissions:
        st.info("No paid commissions yet. Commissions will appear here once deposits or final payments are recorded in the project workflow.")
        st.markdown("""
        <div style="background: rgba(0, 168, 232, 0.1); border-radius: 12px; padding: 16px; margin-top: 16px;">
            <h5 style="color: #00A8E8; margin: 0 0 8px 0;">How Commissions Are Tracked</h5>
            <ul style="color: #E5E5E5; font-size: 13px; margin: 0; padding-left: 20px;">
                <li><strong>Deposit Received</strong> - When you confirm deposit in Block D (Deposit & Handoff)</li>
                <li><strong>Final Payment</strong> - When you close a project in Block G (Project Closeout)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        return
    
    total_payments = sum(float(c.get("payment_amount") or 0) for c in commissions)
    avg_commission_rate = sum(float(c.get("commission_rate") or 10) for c in commissions) / len(commissions) if commissions else 10
    total_commission = sum(
        float(c.get("payment_amount") or 0) * float(c.get("commission_rate") or 10) / 100 
        for c in commissions
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Payments", f"${total_payments:,.2f}")
    with col2:
        st.metric("Total Commission", f"${total_commission:,.2f}")
    with col3:
        st.metric("Payment Count", len(commissions))
    
    st.divider()
    
    report_period_comms = get_report_period_commissions(commissions)
    date_range = get_current_period_date_range()
    
    today = today_mountain()
    is_deadline_day = today.day == 16 or today.day == 1
    period_label = "Due Period" if is_deadline_day else "Current Period"
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        border: 1px solid {'#FF6B35' if is_deadline_day else '#00A8E8'};
    ">
        <h4 style="color: {'#FF6B35' if is_deadline_day else '#00A8E8'}; margin: 0 0 8px 0;">{period_label}: {date_range}</h4>
        <p style="color: #888; font-size: 13px; margin: 0;">
            {len(report_period_comms)} payment(s) in this period
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Generate & Send Commission Report", type="primary", use_container_width=True):
        if report_period_comms:
            send_current_period_report(report_period_comms, date_range)
        else:
            st.warning("No payments in this period to report.")
    
    st.divider()
    st.markdown("### Payment History by Period")
    
    grouped = group_commissions_by_period(commissions)
    
    for (year, month, period_num), period_data in grouped:
        month_name = period_data["month_name"]
        period_label = period_data["period_label"]
        paid_on = period_data["paid_on"]
        submission_due = period_data["submission_due"]
        period_commissions = period_data["commissions"]
        
        period_total = sum(float(c.get("payment_amount") or 0) for c in period_commissions)
        period_commission = sum(
            float(c.get("payment_amount") or 0) * float(c.get("commission_rate") or 10) / 100 
            for c in period_commissions
        )
        
        today = today_mountain()
        is_current = (year == today.year and month == today.month and period_num == get_current_period())
        
        with st.expander(f"{month_name} - Period {period_num} ({period_label})", expanded=is_current):
            st.markdown(f"""
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 12px 16px;
                margin-bottom: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <div>
                    <span style="color: #00A8E8; font-weight: 600;">{paid_on}</span>
                    <span style="color: #888; margin-left: 16px;">{submission_due}</span>
                </div>
                <div>
                    <span style="color: #888;">Period Total:</span> 
                    <strong style="color: #4CAF50;">${period_total:,.2f}</strong>
                    <span style="color: #888; margin-left: 12px;">Commission:</span>
                    <strong style="color: #FFB800;">${period_commission:,.2f}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            for comm in period_commissions:
                client = comm.get("client_name", "Unknown")
                project_value = float(comm.get("project_value") or 0)
                payment_amount = float(comm.get("payment_amount") or 0)
                rate = float(comm.get("commission_rate") or 10)
                payment_date = comm.get("payment_date")
                payment_type = comm.get("payment_type", "deposit")
                notes = comm.get("commission_notes") or ""
                
                commission_earned = payment_amount * rate / 100
                type_label = "Final" if payment_type == "final" else "Deposit"
                type_color = "#4CAF50" if payment_type == "final" else "#00A8E8"
                
                st.markdown(f"""
                <div style="
                    background: #0d1b2a;
                    border-radius: 10px;
                    padding: 12px 16px;
                    margin-bottom: 8px;
                    border-left: 3px solid {type_color};
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #E5E5E5; font-size: 15px;">{client}</strong>
                            <span style="
                                background: {type_color};
                                color: white;
                                padding: 2px 8px;
                                border-radius: 4px;
                                font-size: 11px;
                                margin-left: 8px;
                            ">{type_label}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #888; font-size: 12px;">{payment_date}</span>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                        <div>
                            <span style="color: #888; font-size: 12px;">Project: </span>
                            <span style="color: #E5E5E5;">${project_value:,.2f}</span>
                            <span style="color: #888; font-size: 12px; margin-left: 12px;">Payment: </span>
                            <span style="color: #4CAF50;">${payment_amount:,.2f}</span>
                        </div>
                        <div>
                            <span style="color: #888; font-size: 12px;">Commission ({rate:.0f}%): </span>
                            <strong style="color: #FFB800;">${commission_earned:,.2f}</strong>
                        </div>
                    </div>
                    {f'<div style="color: #888; font-size: 11px; font-style: italic; margin-top: 6px;">{notes}</div>' if notes else ''}
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"Send Report", key=f"send_report_{year}_{month}_{period_num}"):
                    send_period_report(year, month, period_num, period_commissions, period_label)
    
    st.divider()
    render_pay_schedule_reminder()


def render_all_projects_tab():
    """Render the editable projects table for commission rate adjustments."""
    st.markdown(
        '<p style="color: #888; font-size: 14px;">Edit commission rates for all projects. Changes save automatically.</p>',
        unsafe_allow_html=True
    )
    
    projects = get_all_projects_for_ledger()
    
    if not projects:
        st.info("No projects in the ledger yet.")
        return
    
    df = pd.DataFrame(projects)
    
    df["estimated_value"] = pd.to_numeric(df["estimated_value"], errors="coerce").fillna(0)
    df["commission_rate"] = pd.to_numeric(df["commission_rate"], errors="coerce").fillna(10.0)
    df["commission_amount"] = (df["estimated_value"] * df["commission_rate"] / 100).round(2)
    
    display_df = df[["id", "client_name", "status", "estimated_value", "commission_rate", "commission_amount"]].copy()
    display_df.columns = ["ID", "Client", "Status", "Project Value ($)", "Commission (%)", "Est. Commission ($)"]
    
    column_config = {
        "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "Client": st.column_config.TextColumn("Client", disabled=True, width="medium"),
        "Status": st.column_config.TextColumn("Status", disabled=True, width="small"),
        "Project Value ($)": st.column_config.NumberColumn(
            "Project Value ($)",
            format="$%.2f",
            disabled=True,
            width="medium"
        ),
        "Commission (%)": st.column_config.NumberColumn(
            "Commission (%)",
            format="%.1f%%",
            min_value=0,
            max_value=100,
            step=0.5,
            width="small"
        ),
        "Est. Commission ($)": st.column_config.NumberColumn(
            "Est. Commission ($)",
            format="$%.2f",
            disabled=True,
            width="medium"
        )
    }
    
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key="ledger_editor",
        num_rows="fixed"
    )
    
    if "ledger_editor" in st.session_state:
        for idx, row in edited_df.iterrows():
            original_row = display_df.iloc[idx]
            
            if row["Commission (%)"] != original_row["Commission (%)"]:
                success = update_project_ledger(
                    str(row["ID"]),
                    float(row["Commission (%)"])
                )
                
                if success:
                    st.toast(f"Updated {row['Client']}")


def send_current_period_report(commissions: list, date_range: str):
    """Generate and send commission report for the current period."""
    report_lines = []
    total_payment = 0
    total_commission = 0
    
    for comm in commissions:
        client = comm.get("client_name", "Unknown")
        payment_amount = float(comm.get("payment_amount") or 0)
        rate = float(comm.get("commission_rate") or 10)
        payment_type = comm.get("payment_type", "deposit")
        payment_date = comm.get("payment_date")
        notes = comm.get("commission_notes") or ""
        
        commission_earned = payment_amount * rate / 100
        type_label = "Final Payment" if payment_type == "final" else "Deposit"
        
        total_payment += payment_amount
        total_commission += commission_earned
        
        line = f"- {client} ({type_label} on {payment_date}): ${payment_amount:,.2f} -> Commission ({rate:.0f}%): ${commission_earned:,.2f}"
        if notes:
            line += f"\n  Note: {notes}"
        report_lines.append(line)
    
    report_body = f"""Commission Report
Period: {date_range}

SUMMARY
-------
Total Payments Received: ${total_payment:,.2f}
Total Commission Earned: ${total_commission:,.2f}
Number of Payments: {len(commissions)}

DETAILS
-------
{chr(10).join(report_lines)}

---
Generated by Grayco Lite V3 on {now_mountain().strftime('%B %d, %Y at %I:%M %p')} (MT)
"""
    
    subject = f"Commission Report - {date_range}"
    
    success = send_commission_report_email(subject, report_body)
    
    if success:
        st.success(f"Commission report sent for {date_range}")
    else:
        st.error("Failed to send report. Please check email settings.")


def send_period_report(year: int, month: int, period_num: int, commissions: list, period_label: str):
    """Generate and send commission report for a specific period."""
    month_name = datetime(year, month, 1).strftime("%B %Y")
    
    if period_num == 1:
        date_range = f"{month_name} 1st - 15th"
    else:
        last_day = monthrange(year, month)[1]
        date_range = f"{month_name} 16th - {last_day}th"
    
    send_current_period_report(commissions, date_range)


def render_pay_schedule_reminder():
    """Render the pay schedule reminder section."""
    st.markdown("""
    <div style="
        background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
        border-radius: 16px;
        padding: 20px;
        margin-top: 16px;
        border: 1px solid #00A8E8;
    ">
        <h4 style="color: #00A8E8; margin: 0 0 12px 0;">Pay Schedule Reminder</h4>
        <div style="
            background: rgba(255, 184, 0, 0.1);
            border-radius: 8px;
            padding: 12px;
        ">
            <div style="color: #E5E5E5; font-size: 13px;">
                <div style="margin-bottom: 6px;">
                    <strong>Period 1 (1st - 15th)</strong>: Submit by 16th - Paid on 20th
                </div>
                <div>
                    <strong>Period 2 (16th - EOM)</strong>: Submit by 1st - Paid on 5th
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
