from pyrogram import types

class Buttons:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def terms_keyboard(self):
        return self.ikm([
            [
                self.ikb(
                    text="✅ Agree",
                    callback_data="terms_agree",
                ),
                self.ikb(
                    text="❌ Disagree",
                    callback_data="terms_disagree",
                ),
            ]
        ])

    def force_join_keyboard(self, channel1, channel2):
        return self.ikm([
            [
                self.ikb(
                    text="📢 Join Channel 1",
                    url=f"https://t.me/{channel1.replace('@', '')}",
                ),
            ],
            [
                self.ikb(
                    text="📢 Join Channel 2",
                    url=f"https://t.me/{channel2.replace('@', '')}",
                ),
            ],
            [
                self.ikb(
                    text="✅ Verify",
                    callback_data="force_join_check",
                ),
            ],
        ])

    def main_menu(self, is_admin=False):
        rows = [
            [
                self.ikb(
                    text="📱 My Accounts",
                    callback_data="menu_accounts",
                ),
                self.ikb(
                    text="👥 Groups",
                    callback_data="menu_groups",
                ),
            ],
            [
                self.ikb(
                    text="✉️ Messaging",
                    callback_data="menu_messaging",
                ),
                self.ikb(
                    text="🤖 AI Chat",
                    callback_data="menu_ai_chat",
                ),
            ],
            [
                self.ikb(
                    text="🔗 Join Groups",
                    callback_data="menu_join",
                ),
                self.ikb(
                    text="📊 Stats",
                    callback_data="menu_stats",
                ),
            ],
            [
                self.ikb(
                    text="💎 Premium",
                    callback_data="menu_premium",
                ),
                self.ikb(
                    text="❓ Help",
                    callback_data="menu_help",
                ),
            ],
            [
                self.ikb(
                    text="📞 Contact",
                    url="https://t.me/dotshv",
                ),
            ],
        ]
        if is_admin:
            rows.append([
                self.ikb(
                    text="⚙️ Admin Panel",
                    callback_data="menu_admin",
                ),
            ])
        return self.ikm(rows)

    def back_to_menu(self):
        return self.ikm([
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ]
        ])

    def account_select_groups(self, accounts):
        rows = []
        for acc in accounts:
            phone = acc.get("phone", "Unknown")
            rows.append([
                self.ikb(
                    text=f"📱 {phone}",
                    callback_data=f"grp_acc_{phone}",
                )
            ])
        if not rows:
            rows.append([
                self.ikb(
                    text="No accounts found. Add accounts first.",
                    callback_data="menu_accounts",
                ),
            ])
        rows.append([
            self.ikb(
                text="🔙 Back to Menu",
                callback_data="back_menu",
            ),
        ])
        return self.ikm(rows)

    def account_select_ai(self, accounts):
        rows = []
        for acc in accounts:
            phone = acc.get("phone", "Unknown")
            rows.append([
                self.ikb(
                    text=f"📱 {phone}",
                    callback_data=f"ai_acc_{phone}",
                )
            ])
        if not rows:
            rows.append([
                self.ikb(
                    text="No accounts found. Add accounts first.",
                    callback_data="menu_accounts",
                ),
            ])
        rows.append([
            self.ikb(
                text="🔙 Back to AI Menu",
                callback_data="menu_ai_chat",
            ),
        ])
        return self.ikm(rows)

    def account_list(self, accounts):
        rows = []
        for acc in accounts:
            phone = acc.get("phone", "Unknown")
            rows.append([
                self.ikb(
                    text=f"{phone}",
                    callback_data=f"acc_info_{phone}",
                ),
                self.ikb(
                    text="🗑 Remove",
                    callback_data=f"acc_remove_{phone}",
                ),
            ])
        rows.append([
            self.ikb(
                text="➕ Add Account",
                callback_data="acc_add",
            ),
        ])
        rows.append([
            self.ikb(
                text="🔙 Back to Menu",
                callback_data="back_menu",
            ),
        ])
        return self.ikm(rows)

    def account_remove_confirm(self, phone):
        return self.ikm([
            [
                self.ikb(
                    text="✅ Yes, Remove",
                    callback_data=f"acc_confirm_remove_{phone}",
                ),
                self.ikb(
                    text="❌ Cancel",
                    callback_data="menu_accounts",
                ),
            ]
        ])

    def group_list(self, groups, phone, page=1):
        ITEMS_PER_PAGE = 15
        rows = []
        seen = set()
        
        # Deduplicate groups
        unique_groups = []
        for grp in groups:
            gid = grp["group_id"]
            if gid in seen:
                continue
            seen.add(gid)
            unique_groups.append(grp)
            
        total_pages = max(1, (len(unique_groups) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        if page > total_pages:
            page = total_pages
        if page < 1:
            page = 1
            
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_groups = unique_groups[start_idx:end_idx]

        for grp in page_groups:
            gid = grp["group_id"]
            title = grp.get("group_title", "Unknown")[:25]
            enabled = grp.get("enabled", True)
            status = "✅" if enabled else "❌"
            rows.append([
                self.ikb(
                    text=f"[{status}] {title}",
                    callback_data=f"grp_manage_{phone}_{gid}",
                )
            ])
            
        if not rows:
            rows.append([
                self.ikb(
                    text="No groups found.",
                    callback_data="ignore",
                ),
            ])
            
        # Pagination controls
        if total_pages > 1:
            nav_row = []
            if page > 1:
                nav_row.append(self.ikb(text="◀️ Previous", callback_data=f"grp_page_{phone}_{page-1}"))
            nav_row.append(self.ikb(text=f"📄 {page}/{total_pages}", callback_data="ignore"))
            if page < total_pages:
                nav_row.append(self.ikb(text="Next ▶️", callback_data=f"grp_page_{phone}_{page+1}"))
            rows.append(nav_row)

        rows.append([
            self.ikb(
                text="🔄 Refresh Groups",
                callback_data="grp_refresh",
            ),
        ])
        rows.append([
            self.ikb(
                text="🔙 Back to Accounts",
                callback_data="menu_groups",
            ),
        ])
        return self.ikm(rows)

    def group_details(self, group, phone):
        gid = group["group_id"]
        enabled = group.get("enabled", True)
        status_text = "✅ Disable" if enabled else "❌ Enable"
        
        return self.ikm([
            [
                self.ikb(
                    text=status_text,
                    callback_data=f"grp_toggle_{phone}_{gid}",
                ),
                self.ikb(
                    text="⏱ Set Time",
                    callback_data=f"grp_time_{phone}_{gid}",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Groups",
                    callback_data=f"grp_acc_{phone}",
                ),
            ],
        ])

    def group_time_options(self, group_id, phone):
        return self.ikm([
            [
                self.ikb(text="1s", callback_data=f"grp_settime_{phone}_{group_id}_1"),
                self.ikb(text="5s", callback_data=f"grp_settime_{phone}_{group_id}_5"),
                self.ikb(text="10s", callback_data=f"grp_settime_{phone}_{group_id}_10"),
                self.ikb(text="30s", callback_data=f"grp_settime_{phone}_{group_id}_30"),
            ],
            [
                self.ikb(text="1m", callback_data=f"grp_settime_{phone}_{group_id}_60"),
                self.ikb(text="5m", callback_data=f"grp_settime_{phone}_{group_id}_300"),
                self.ikb(text="10m", callback_data=f"grp_settime_{phone}_{group_id}_600"),
                self.ikb(text="30m", callback_data=f"grp_settime_{phone}_{group_id}_1800"),
            ],
            [
                self.ikb(text="1h", callback_data=f"grp_settime_{phone}_{group_id}_3600"),
                self.ikb(text="Custom", callback_data=f"grp_settime_{phone}_{group_id}_custom"),
            ],
            [
                self.ikb(
                    text="🔙 Back",
                    callback_data=f"grp_manage_{phone}_{group_id}",
                ),
            ],
        ])

    def payment_methods(self):
        return self.ikm([
            [
                self.ikb(
                    text="⭐ Telegram Stars (Instant)",
                    callback_data="pay_stars",
                ),
            ],
            [
                self.ikb(
                    text="🏦 UPI",
                    callback_data="pay_upi",
                ),
            ],
            [
                self.ikb(
                    text="🪙 USDT (BEP20)",
                    callback_data="pay_usdt",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def payment_approve_reject(self, payment_id, user_id):
        return self.ikm([
            [
                self.ikb(
                    text="✅ Approve",
                    callback_data=f"pay_approve_{payment_id}_{user_id}",
                ),
                self.ikb(
                    text="❌ Reject",
                    callback_data=f"pay_reject_{payment_id}_{user_id}",
                ),
            ]
        ])

    def admin_panel(self):
        return self.ikm([
            [
                self.ikb(
                    text="📊 Global Stats",
                    callback_data="admin_stats",
                ),
                self.ikb(
                    text="📢 Broadcast",
                    callback_data="admin_broadcast",
                ),
            ],
            [
                self.ikb(
                    text="⛔ Suspend",
                    callback_data="admin_suspend",
                ),
                self.ikb(
                    text="✅ Unsuspend",
                    callback_data="admin_unsuspend",
                ),
            ],
            [
                self.ikb(
                    text="💎 Premium Users",
                    callback_data="admin_list_premium",
                ),
                self.ikb(
                    text="❌ Rm Premium",
                    callback_data="admin_rm_premium",
                ),
            ],
            [
                self.ikb(
                    text="ℹ️ User Info",
                    callback_data="admin_userinfo",
                ),
                self.ikb(
                    text="🛠️ Fix User",
                    callback_data="admin_fix_user",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def messaging_controls(self, is_running=False):
        if is_running:
            return self.ikm([
                [
                    self.ikb(
                        text="🛑 Stop Sending",
                        callback_data="msg_stop",
                    ),
                ],
                [
                    self.ikb(
                        text="🔙 Back to Menu",
                        callback_data="back_menu",
                    ),
                ],
            ])
        return self.ikm([
            [
                self.ikb(
                    text="📝 Set Message",
                    callback_data="msg_set",
                ),
            ],
            [
                self.ikb(
                    text="⏱ Set Default Timer",
                    callback_data="msg_timer",
                ),
            ],
            [
                self.ikb(
                    text="▶️ Start Sending",
                    callback_data="msg_start",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def ai_chat_controls(self, is_running=False):
        if is_running:
            return self.ikm([
                [
                    self.ikb(
                        text="🛑 Stop AI Chat",
                        callback_data="ai_stop",
                    ),
                ],
                [
                    self.ikb(
                        text="🔙 Back to Menu",
                        callback_data="back_menu",
                    ),
                ],
            ])
        return self.ikm([
            [
                self.ikb(
                    text="📋 Select Groups",
                    callback_data="ai_select_groups",
                ),
            ],
            [
                self.ikb(
                    text="▶️ Start AI Chat",
                    callback_data="ai_start",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def ai_group_selector(self, groups, phone, selected_ids=None):
        selected_ids = selected_ids or []
        rows = []
        seen = set()
        for grp in groups:
            gid = grp["group_id"]
            if gid in seen:
                continue
            seen.add(gid)
            title = grp.get("group_title", "Unknown")[:25]
            is_sel = gid in selected_ids
            status = "✅" if is_sel else "❌"
            rows.append([
                self.ikb(
                    text=f"[{status}] {title}",
                    callback_data=f"ai_toggle_{phone}_{gid}",
                ),
            ])
        if not rows:
            rows.append([
                self.ikb(
                    text="No groups found.",
                    callback_data="ignore",
                ),
            ])
        rows.append([
            self.ikb(
                text="✅ Confirm Selection",
                callback_data=f"ai_confirm_{phone}",
            ),
        ])
        rows.append([
            self.ikb(
                text="🔙 Back to Accounts",
                callback_data="ai_select_groups",
            ),
        ])
        return self.ikm(rows)

    def help_menu(self):
        return self.ikm([
            [
                self.ikb(
                    text="📱 Accounts",
                    callback_data="help_accounts",
                ),
                self.ikb(
                    text="👥 Groups",
                    callback_data="help_groups",
                ),
            ],
            [
                self.ikb(
                    text="✉️ Messaging",
                    callback_data="help_messaging",
                ),
                self.ikb(
                    text="🤖 AI Chat",
                    callback_data="help_ai",
                ),
            ],
            [
                self.ikb(
                    text="💎 Premium",
                    callback_data="help_premium",
                ),
                self.ikb(
                    text="🔗 Join",
                    callback_data="help_join",
                ),
            ],
            [
                self.ikb(
                    text="📢 Channel",
                    url="https://t.me/AdsGcHelper",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def help_back(self):
        return self.ikm([
            [
                self.ikb(
                    text="🔙 Back to Help",
                    callback_data="menu_help",
                ),
                self.ikb(
                    text="🏠 Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def join_options(self):
        return self.ikm([
            [
                self.ikb(
                    text="🔗 Join Group/Channel",
                    callback_data="join_single",
                ),
            ],
            [
                self.ikb(
                    text="🔗 Bulk Join (Max 10)",
                    callback_data="join_bulk",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def error_resolved(self):
        return self.ikm([
            [
                self.ikb(
                    text="🏠 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])

    def buy_premium_button(self):
        return self.ikm([
            [
                self.ikb(
                    text="💎 Buy Premium",
                    callback_data="menu_premium",
                ),
            ],
            [
                self.ikb(
                    text="🔙 Back to Menu",
                    callback_data="back_menu",
                ),
            ],
        ])
