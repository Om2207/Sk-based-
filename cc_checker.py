import aiohttp
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import STRIPE_SK_KEY, STRIPE_PK_KEY

async def get_bin_info(bin_number):
    url = f"https://ayanlookup-dd2c4f56ceac.herokuapp.com/bin/{bin_number}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return {}

async def get_token(cc, mes, ano, cvv):
    url = "https://api.stripe.com/v1/payment_methods"
    headers = {'Authorization': f'Bearer {STRIPE_PK_KEY}'}
    data = {
        'type': 'card',
        'card[number]': cc,
        'card[cvc]': cvv,
        'card[exp_month]': mes,
        'card[exp_year]': ano,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            result = await response.json()
            token = result.get('id')
            msg = result.get('error', {}).get('message', None)
            return result, token, msg

async def request_charge(token):
    url = "https://api.stripe.com/v1/payment_intents"
    headers = {'Authorization': f'Bearer {STRIPE_SK_KEY}'}
    data = {
        'amount': 100,
        'currency': 'usd',
        'payment_method_types[]': 'card',
        'description': 'Dark_sol Donation',
        'payment_method': token,
        'confirm': 'true',
        'off_session': 'true'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            result = await response.json()
            if response.status == 402:
                error_message = result.get('error', {}).get('message', 'Card declined')
                decline_code = result.get('error', {}).get('decline_code', 'unknown')
                return result, error_message
            elif response.status != 200:
                return result, "Unexpected error occurred"
            return result, None

async def process_cc(cc):
    cc_split = cc.split('|')
    cc_number, mes, ano, cvv = cc_split[0], cc_split[1], cc_split[2], cc_split[3]
    amt = 1
    bin_number = cc_number[:6]

    try:
        bin_info = await get_bin_info(bin_number)
        bank = html.escape(bin_info.get("bank", "Unknown Bank"))
        bin_type = html.escape(bin_info.get("type", "XXXXXX"))
        country = html.escape(bin_info.get("country", "Unknown Country"))
        flag = bin_info.get("flag", "🌍")

        result1, token, msg1 = await get_token(cc_number, mes, ano, cvv)
        if not token:
            return {
                'status': 'Declined',
                'message': (
                    f"[ϟ] CC: <code>{html.escape(cc)}</code>\n"
                    f"[ϟ] Status: Token Error\n"
                    f"[ϟ] Result: {html.escape(str(msg1))}\n"
                    f"[ϟ] Gateway: Failed to Obtain Token\n\n"
                    f"Bin: {bin_type}\n"
                    f"Bank: {bank}\n"
                    f"Country: {country} ({flag})\n\n"
                    f"Bot Made By ➺ <a href='https://t.me/rundilundlegamera'>⏤‌‌𝙊𝗠 「𝗫𝗬」</a>"
                )
            }

        result2, msg2 = await request_charge(token)

        decline_code = result2.get('error', {}).get('decline_code')
        if 'seller_message' in result2 and result2['seller_message'] == 'Payment complete.':
            return {
                'status': 'Charged',
                'message': (
                    f"[ϟ] CC: <code>{html.escape(cc)}</code>\n"
                    f"[ϟ] Status: Charged\n"
                    f"[ϟ] Result: Payment Complete\n"
                    f"[ϟ] Gateway: Stripe Charge ${amt}\n\n"
                    f"Bin: {bin_type}\n"
                    f"Bank: {bank}\n"
                    f"Country: {country} ({flag})\n\n"
                    f"Bot Made By ➺ <a href='https://t.me/rundilundlegamera'>⏤‌‌𝙊𝗠 「𝗫𝗬」</a>"
                )
            }
        elif decline_code:
            response_map = {
                'insufficient_funds': "Insufficient Funds",
                'card_error_authentication_required': "Authentication Required",
                'incorrect_cvc': "CCN Live",
                'transaction_not_allowed': "Transaction Not Allowed",
                'fraudulent': "Fraudulent",
                'expired_card': "Expired Card",
                'generic_decline': "Generic Declined",
                'do_not_honor': "Do Not Honor",
                'rate_limit': "Rate Limit Exceeded",
            }
            response_message = response_map.get(decline_code, "Your Card Was Declined")
            return {
                'status': response_message,
                'message': (
                    f"[ϟ] CC: <code>{html.escape(cc)}</code>\n"
                    f"[ϟ] Status: Declined\n"
                    f"[ϟ] Result: {html.escape(response_message)}\n"
                    f"[ϟ] Gateway: Stripe Charge ${amt}\n\n"
                    f"Bin: {bin_type}\n"
                    f"Bank: {bank}\n"
                    f"Country: {country} ({flag})\n\n"
                    f"Bot Made By ➺ <a href='https://t.me/rundilundlegamera'>⏤‌‌𝙊𝗠 「𝗫𝗬」</a>"
                )
            }
        else:
            return {
                'status': 'Declined',
                'message': (
                    f"[ϟ] CC: <code>{html.escape(cc)}</code>\n"
                    f"[ϟ] Status: Declined\n"
                    f"[ϟ] Result: Unknown Error: {html.escape(str(msg1))} - {html.escape(str(msg2))}\n"
                    f"[ϟ] Gateway: Stripe Charge Failed\n\n"
                    f"Bin: {bin_type}\n"
                    f"Bank: {bank}\n"
                    f"Country: {country} ({flag})\n\n"
                    f"Bot Made By ➺ <a href='https://t.me/rundilundlegamera'>⏤‌‌𝙊𝗠 「𝗫𝗬」</a>"
                )
            }
    except Exception as e:
        return {
            'status': 'Declined',
            'message': (
                f"[ϟ] CC: <code>{html.escape(cc)}</code>\n"
                f"[ϟ] Status: Declined\n"
                f"[ϟ] Result: Internal Error\n"
                f"[ϟ] Gateway: Stripe Charge Failed\n\n"
                f"Bin: {bin_type}\n"
                f"Bank: {bank}\n"
                f"Country: {country} ({flag})\n\n"
                f"Bot Made By ➺ <a href='https://t.me/rundilundlegamera'>⏤‌‌𝙊𝗠 「𝗫𝗬」</a>"
            )
        }

async def send_cc_result(update, cc, status, result, amt, bin_type, bank, country, flag):
    message = (
        f"[ϟ] CC: <code>{html.escape(cc)}</code>\n"
        f"[ϟ] Status: {status}\n"
        f"[ϟ] Result: {result}\n"
        f"[ϟ] Gateway: Stripe Charge ${amt}\n\n"
        f"Bin: {bin_type}\n"
        f"Bank: {bank}\n"
        f"Country: {country} ({flag})\n\n"
        f"Bot Made By ➺ <a href='https://t.me/rundilundlegamera'>⏤‌‌𝙊𝗠 「𝗫𝗬」</a>"
    )
    await update.message.reply_html(message)

async def mass_check_cc(update, context, file, mass_checking_status):
    user_id = update.effective_user.id
    message = await update.message.reply_text("CC checking started. Please wait...")
    file_content = await file.download_as_bytearray()
    cc_list = file_content.decode().splitlines()

    results = {
        'charged': [],
        'cvv_live': [],
        'ccn_live': [],
        'insufficient_funds': [],
        'declined': []
    }

    keyboard = [
        [InlineKeyboardButton("Charged (0)", callback_data="charged"),
         InlineKeyboardButton("CVV Live (0)", callback_data="cvv_live")],
        [InlineKeyboardButton("CCN Live (0)", callback_data="ccn_live"),
         InlineKeyboardButton("Insufficient Funds (0)", callback_data="insufficient_funds")],
        [InlineKeyboardButton("Declined (0)", callback_data="declined")],
        [InlineKeyboardButton("Stop Checking", callback_data="stop_checking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.edit_text("CC checking in progress...", reply_markup=reply_markup)

    for i, cc in enumerate(cc_list):
        if not mass_checking_status.get(user_id, False):
            await message.edit_text("CC checking stopped.", reply_markup=None)
            return

        result = await process_cc(cc)
        status = result['status']

        if status == 'Charged':
            results['charged'].append(cc)
        elif status == 'CVV Live':
            results['cvv_live'].append(cc)
        elif status == 'CCN Live':
            results['ccn_live'].append(cc)
        elif status == 'Insufficient Funds':
            results['insufficient_funds'].append(cc)
        else:
            results['declined'].append(cc)

        if status in ['Charged', 'CVV Live', 'CCN Live', 'Insufficient Funds']:
            # Extract necessary information from the result
            cc_info = cc.split('|')
            amt = 1  # Assuming $1 charge for all CCs
            bin_info = await get_bin_info(cc_info[0][:6])
            bin_type = html.escape(bin_info.get("type", "XXXXXX"))
            bank = html.escape(bin_info.get("bank", "Unknown Bank"))
            country = html.escape(bin_info.get("country", "Unknown Country"))
            flag = bin_info.get("flag", "🌍")

            # Send the result immediately
            await send_cc_result(update, cc, status, result['message'].split('\n')[2].split(': ')[1], amt, bin_type, bank, country, flag)

        # Update the keyboard with current counts
        keyboard = [
            [InlineKeyboardButton(f"Charged ({len(results['charged'])})", callback_data="charged"),
             InlineKeyboardButton(f"CVV Live ({len(results['cvv_live'])})", callback_data="cvv_live")],
            [InlineKeyboardButton(f"CCN Live ({len(results['ccn_live'])})", callback_data="ccn_live"),
             InlineKeyboardButton(f"Insufficient Funds ({len(results['insufficient_funds'])})", callback_data="insufficient_funds")],
            [InlineKeyboardButton(f"Declined ({len(results['declined'])})", callback_data="declined")],
            [InlineKeyboardButton("Stop Checking", callback_data="stop_checking")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.edit_text(f"CC checking in progress... ({i+1}/{len(cc_list)})", reply_markup=reply_markup)

    # Summarize results
    summary = "CC Checking Results:\n\n"
    for status, ccs in results.items():
        summary += f"{status.replace('_', ' ').title()}: {len(ccs)}\n"

    await message.edit_text(summary, reply_markup=reply_markup)
    mass_checking_status[user_id] = False