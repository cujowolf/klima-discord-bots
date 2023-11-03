import os
import json
import math

import requests
from discord.ext import tasks
from subgrounds.subgrounds import Subgrounds

from utils import (
    get_discord_client,
    update_nickname,
    update_presence,
    get_last_metric,
    get_last_carbon,
)

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

# Initialized Discord client
client = get_discord_client()

sg = Subgrounds()


def get_rebases_per_day():
    """
    Calculates the average number of rebases per day based on the average
    block production time for the previous 1 million blocks
    """
    avg_block_secs = float(
        json.loads(requests.get("https://klimadao.finance/api/block-rate").content)[
            "blockRate30Day"
        ]
    )

    secs_per_rebase = 11520 * avg_block_secs

    return 24 / (secs_per_rebase / 60 / 60)


def get_info():
    last_metric = get_last_metric(sg)
    total_carbon = sg.query([last_metric.treasuryCarbon])

    last_carbon = get_last_carbon(sg)
    current_sma, credit_supply = sg.query(
        [last_carbon.creditSMA, last_carbon.creditSupply]
    )
    return total_carbon, current_sma, credit_supply


@client.event
async def on_ready():
    print("Logged in as {0.user}".format(client))
    if not update_info.is_running():
        update_info.start()


@tasks.loop(seconds=300)
async def update_info():
    rebases_per_day = get_rebases_per_day()

    treasury_carbon, carbon_sma, credit_supply = get_info()

    carbon_sma = carbon_sma / 1e18
    credit_supply = credit_supply / 1e18

    print(treasury_carbon)
    print(carbon_sma)
    if (
        treasury_carbon is not None
        and carbon_sma is not None
        and rebases_per_day is not None
    ):
        sma_percent = carbon_sma / credit_supply
        # ie, annualized reward %
        supply_change_annual = math.pow(1 + sma_percent, 365 * rebases_per_day) - 1
    else:
        return

    yield_text = f"{supply_change_annual*100:,.2f}% DCM Supply"
    print(yield_text)

    success = await update_nickname(client, yield_text)
    if not success:
        return

    success = await update_presence(
        client, f"{carbon_sma:,.2f} Δ supply per epoch", "watching"
    )
    if not success:
        return


client.run(BOT_TOKEN)
