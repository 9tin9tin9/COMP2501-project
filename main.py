#!/usr/local/bin/python3

from pytwitter import Api
from dotenv import load_dotenv
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
from dateutil.parser import parse
from time import sleep, strftime

refresh_influencer = True
refresh_followers = True
refresh_follower_tweets = True

date_r = "27-4-23"

class Twitter:
    def __init__(self):
        load_dotenv()
        self.api = Api(bearer_token = os.environ["bearer_token"])

    def load_tweets(self, usernames, count = 10):
        query = " ".join(["-is:retweet", "-is:reply", "lang:en"]) + " (" + \
                " OR ".join([f"from:{x}" for x in usernames]) + ")"
        total = count
        print(f"Requesting {count} tweets with query \"{query}\"")
        tweets = []
        next_page = None
        while True:
            try:
                response = self.api.search_tweets(
                    query = query,
                    tweet_fields = [
                        "context_annotations", "entities", "created_at"],
                    max_results = min(count, 100),
                    return_json = True)
            except:
                print(f"Only got {len(tweets)}/{total} tweets")
                return tweets
            tweets += response["data"] if "data" in response else []
            next_page = response["meta"]["next_token"] \
                if "next_token" in response["meta"] \
                else None
            count -= response["meta"]["result_count"]
            print(f"{count} tweets left to request. "
                  f"Next page token: {next_page}")

            if count > 0 and next_page != None:
                sleep(2)
            else:
                break

        return tweets

    def get_followers(self, userid, count = 1000):
        print(f"Requesting {count} followers of {userid}")
        followers = []
        next_page = None
        while count > 0:
            param = {
                "user_id": userid,
                "max_results": min(1000, count),
                "user_fields": [
                    "description",
                    "location",
                    "public_metrics",
                    "protected",
                    "verified"
                ],
                "pagination_token": next_page,
                "return_json": True,
            }
            response = self.api.get_followers(**param)
            followers += response["data"]
            next_page = response["meta"]["next_token"]
            count -= response["meta"]["result_count"]
            print(f"{count} followers left to request. "
                  f"Next page token: {next_page}")
        return followers

    def get_userids(self, usernames):
        data = self.api.get_users(usernames=usernames).data
        return dict(map(
            lambda x: (x.username, { "id": x.id, "name": x.name } ),
            data))


def get_tweets_from_influencer(twitter, influencer):
    print(f"Getting tweets from {influencer}")

    if refresh_influencer:
        response = twitter.load_tweets([influencer])
        Path(f"tweets/{date_r}/{influencer}/tweets.json") \
            .write_text(json.dumps(response, indent = 4))
        print(f"Wrote json to tweets/{date_r}/{influencer}/tweets.json")
        return response

    else:
        print(f"Load json from tweets/{date_r}/{influencer}/tweets.json")
        return json.loads(
            Path(f"./tweets/{date_r}/{influencer}/tweets.json").read_bytes())


def get_followers_of_influencer(twitter, influencer):
    print(f"Get followers of {influencer}");
    if refresh_followers:
        useful_users = lambda user: \
            not user["protected"] and \
            user["public_metrics"]["tweet_count"] != 0 and \
            user["public_metrics"]["following_count"] > 10
        followers = twitter.get_followers(influencer_data["id"], 3000)
        followers = list(filter(useful_users, followers))
        Path(f"./tweets/{date_r}/{influencer}/followers.json") \
            .write_text(json.dumps(followers, indent = 4))
        print(f"Wrote json to ./tweets/{date_r}/{influencer}/followers.json")
        return followers

    else:
        print(f"Load json from ./tweets/{date_r}/{influencer}/followers.json")
        return json.loads(
            Path(f"./tweets/{date_r}/{influencer}/followers.json").read_bytes())
    

def get_tweets_from_followers(twitter, influencer, followers):
    print(f"Getting tweets from followers of {influencer}")
    if refresh_follower_tweets:
        since = oldest_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        n = 20
        chunks = [
            followers[i * n:(i + 1) * n]
            for i in range((len(followers) + n - 1) // n)]
        tweets = []
        for chunk in chunks:
            tweets += twitter.load_tweets(
                [x["username"] for x in chunk],
                count = 5000 // len(chunks))
        Path(f"./tweets/{date_r}/{influencer}/follower_tweets.json") \
            .write_text(json.dumps(tweets, indent = 4))
        print(f"Wrote json to ./tweets/{date_r}/{influencer}/follower_tweets.json")
        return tweets

    else:
        print(f"Load json from ./tweets/{date_r}/{influencer}/follower_tweets.json")
        return json.loads(
            Path(f"./tweets/{date_r}/{influencer}/follower_tweets.json").read_bytes())

if __name__ == "__main__":
    twitter = Twitter()
    influencers = twitter.get_userids([
        "JoeBiden",
        "elonmusk",
        "CNN",
        "HillaryClinton",
    ])
    for (influencer, influencer_data) in influencers.items():
        Path(f"./tweets/{date_r}/{influencer}").mkdir(parents=True, exist_ok=True)
        response = get_tweets_from_influencer(twitter, influencer)
        followers = get_followers_of_influencer(twitter, influencer)
        dates_tuple = {
            parse(x["created_at"]): x["id"]
            for x in response
        }
        oldest_date = min(dates_tuple) - timedelta(days = 1)
        get_tweets_from_followers(twitter, influencer, followers)
