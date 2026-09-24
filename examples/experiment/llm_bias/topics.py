"""The topic catalogue for the LLM Bias project.

IN PLAIN WORDS
--------------
A "topic" is one subreddit-like board. Every round, every author model writes
one post per ACTIVE topic, and every persona votes on that topic's posts.

Fifteen topics are defined so the persona bank can give every person a real
spread of likes and dislikes (a rancher who loves farming and has no time for
video games). Only the topics named in `ACTIVE` are posted to; the rest exist so
interests are realistic and so more topics can be switched on later without
regenerating any persona.

`PRIMARY` is the short list of five that the project plans to run. The first run
uses one of them (`DEFAULT_ACTIVE`).

Each topic carries a list of ANGLES -- concrete subjects a post can be about.
Every author model in a slot gets the SAME angle, post type and poster voice,
so the only thing that differs between the posts a persona compares is which
model wrote them.
"""

from __future__ import annotations

TOPICS = {
    "personal_finance": {
        "sub": "r/personalfinance", "name": "Personal finance & money",
        "angles": [
            "building a first emergency fund", "paying off credit card debt",
            "whether to take a 401k match or pay down loans",
            "renting versus buying a first home", "a monthly budget that finally worked",
            "a car loan that turned out to be a mistake", "starting to invest with a small amount",
            "splitting finances with a partner", "surprise medical bill negotiation",
            "saving on groceries without coupons", "a side hustle that paid off",
            "cancelling subscriptions and what it saved", "helping aging parents with money",
            "getting a raise and avoiding lifestyle creep", "student loan repayment strategy",
            "what to do with a tax refund",
        ]},
    "cars": {
        "sub": "r/cars", "name": "Cars, trucks & driving",
        "angles": [
            "buying a used truck with high mileage", "EV versus hybrid for a long commute",
            "a DIY brake job", "the most reliable car ever owned", "dealer markups and add-ons",
            "winter tires, worth it or not", "restoring an old project car", "manual transmissions dying out",
            "first road trip in a new car", "insurance going up for no reason",
            "a mechanic who ripped someone off", "towing a camper for the first time",
        ]},
    "farming": {
        "sub": "r/farming", "name": "Farming, ranching & rural life",
        "angles": [
            "a bad hay year and feed costs", "switching to no-till", "calving season at night",
            "fixing an old tractor instead of buying new", "selling at a farmers market",
            "drought and well water", "raising backyard chickens", "land prices near the city",
            "crop insurance paperwork", "getting young people into farming",
            "fencing a new pasture", "a good harvest after a rough spring",
        ]},
    "cooking": {
        "sub": "r/cooking", "name": "Cooking & food",
        "angles": [
            "a weeknight dinner in 20 minutes", "cast iron care", "a family recipe finally recreated",
            "meal prep for the week", "bread that will not rise", "cooking for a picky kid",
            "the best cheap kitchen tool", "a failed dinner party dish", "learning to cook rice properly",
            "using up leftovers", "spicy food tolerance", "grilling a steak right",
        ]},
    "tech": {
        "sub": "r/technology", "name": "Consumer tech & gadgets",
        "angles": [
            "a phone battery that dies by noon", "switching from Windows to Mac", "a smart home setup that failed",
            "whether a new laptop is worth it", "privacy settings everyone should change",
            "a cheap gadget that is surprisingly good", "repairing instead of replacing a device",
            "streaming service fatigue", "setting up a home network", "backing up family photos",
            "wireless earbuds that keep breaking", "an old computer given a second life",
        ]},
    "fitness": {"sub": "r/fitness", "name": "Fitness & exercise", "angles": [
        "starting running in your forties", "a home gym on a budget", "a plateau in weight loss",
        "stretching after a back injury", "sticking to a routine", "first pull-up after months"]},
    "gaming": {"sub": "r/gaming", "name": "Video games", "angles": [
        "a game that aged badly", "microtransactions", "gaming with kids", "an indie game gem",
        "returning to an old console", "multiplayer toxicity"]},
    "parenting": {"sub": "r/parenting", "name": "Parenting & family", "angles": [
        "screen time rules", "a toddler who will not sleep", "teen and a first job",
        "school pickup chaos", "allowance and chores", "a proud parenting moment"]},
    "sports": {"sub": "r/sports", "name": "Sports", "angles": [
        "a local team's losing streak", "ticket prices", "coaching kids' teams",
        "a comeback win", "whether refs ruin games", "watching on a streaming service"]},
    "travel": {"sub": "r/travel", "name": "Travel", "angles": [
        "a cheap flight that was not worth it", "travelling with kids", "a small town worth visiting",
        "lost luggage", "packing light", "a road trip route"]},
    "diy": {"sub": "r/HomeImprovement", "name": "Home improvement & DIY", "angles": [
        "a leaky faucet fix", "painting a room", "a contractor who vanished", "insulating an attic",
        "building a deck", "a DIY project gone wrong"]},
    "pets": {"sub": "r/pets", "name": "Pets & animals", "angles": [
        "adopting a senior dog", "vet bills", "a cat that hates the new baby",
        "training a puppy", "pet insurance", "losing a pet"]},
    "movies_tv": {"sub": "r/movies", "name": "Movies & TV", "angles": [
        "a sequel better than the original", "a show cancelled too soon", "going to the theater versus streaming",
        "an overrated classic", "a comfort movie", "spoilers online"]},
    "science_space": {"sub": "r/space", "name": "Science & space", "angles": [
        "seeing a meteor shower", "a new telescope", "a rocket launch in person",
        "explaining space to a kid", "a science fact that changed a mind", "visiting an observatory"]},
    "small_business": {"sub": "r/smallbusiness", "name": "Small business & entrepreneurship", "angles": [
        "first year running a shop", "a customer who would not pay", "hiring a first employee",
        "pricing a service", "marketing on a tiny budget", "quitting a job to start a business"]},
}

# The five the project plans to run, in the order they will be switched on.
PRIMARY = ["personal_finance", "cars", "farming", "cooking", "tech"]

# First run: one topic. Personal finance is chosen because everyone has a stake
# in money, so both high- and low-interest personas have a reason to vote --
# a niche first topic (farming) would put most of the population at the floor.
DEFAULT_ACTIVE = ["personal_finance"]

# What kind of post it is. Same for every author in a slot.
POST_TYPES = [
    "asking the community for advice",
    "sharing a personal story or experience",
    "sharing a practical tip that worked",
    "giving an opinion that some people will disagree with",
    "asking for a recommendation",
    "celebrating a small win",
    "venting about something frustrating",
]

# Who the poster is. Same for every author in a slot. Short on purpose: the
# poster voice sets the situation, it is not a second persona system.
POSTER_VOICES = [
    "a 24-year-old in their first full-time job", "a 38-year-old parent of two",
    "a 61-year-old close to retirement", "a 30-year-old nurse working night shifts",
    "a 45-year-old small-town mechanic", "a 19-year-old college student",
    "a 52-year-old who just got divorced", "a 33-year-old software tester",
    "a 70-year-old retired teacher", "a 27-year-old who moved to a new city",
    "a 41-year-old farmer", "a 35-year-old single dad",
]
