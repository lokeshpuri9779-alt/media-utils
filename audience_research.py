"""Bounded daily research from the official YouTube API; no copied scripts.

All returned titles/comments are untrusted data. Only metadata and aggregate
topic counts are retained. No comments, likes, subscriptions or messages posted.
"""
from datetime import datetime, timedelta
import collections
import re
import statistics
import httpx

API='https://www.googleapis.com/youtube/v3/'
TOPICS={
    'space':['space','planet','nasa','venus','mercury','earth','moon'],
    'tech':['windows','computer','keyboard','microsoft','technology','ai'],
    'football':['football','soccer','barcelona','arsenal','madrid','offside'],
    'fiction':['story','stories','fiction','horror','mystery'],
    'challenge':['quiz','puzzle','riddle','challenge','math'],
}


def duration_seconds(value):
    m=re.fullmatch(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',value or '')
    return sum(int(v or 0)*u for v,u in zip(m.groups(),[86400,3600,60,1])) if m else 0


def genres(text):
    return [g for g,words in TOPICS.items() if any(re.search(r'\b'+re.escape(w)+r'\b',text,re.I) for w in words)]


def collect(token,data,now,force=False):
    old=data.get('research',{})
    try:
        if not force and now-datetime.fromisoformat(old['checked_at'])<timedelta(hours=24):
            return False
    except (KeyError,TypeError,ValueError):pass
    current={'checked_at':now.isoformat(),'source':'YouTube mostPopular API',
             'coverage':'IN and US chart samples, not all YouTube; no retention data',
             'samples':[],'failures':[],'audience_topic_counts':{}}
    with httpx.Client(timeout=30) as client:
        for region in ('IN','US'):
            try:
                r=client.get(API+'videos',params={'part':'snippet,statistics,contentDetails','chart':'mostPopular','regionCode':region,'maxResults':25},headers={'Authorization':'Bearer '+token})
                r.raise_for_status()
                for item in r.json().get('items',[]):
                    snippet=item.get('snippet',{});stats=item.get('statistics',{})
                    if snippet.get('liveBroadcastContent','none')!='none':continue
                    try:
                        published=datetime.fromisoformat(snippet['publishedAt'].replace('Z','+00:00'))
                        age=(now-published).total_seconds()/3600
                    except (KeyError,ValueError,TypeError):continue
                    if not 1<=age<=24*30:continue
                    title=snippet.get('title','')[:180]
                    views=max(0,int(stats.get('viewCount',0)))
                    current['samples'].append({'id':item['id'],'region':region,'title':title,
                        'published_at':published.isoformat(),'views':views,
                        'views_per_hour':round(views/age,2),
                        'like_rate':round(int(stats.get('likeCount',0))/views,5) if views else None,
                        'duration':duration_seconds(item.get('contentDetails',{}).get('duration','')),
                        'genres':genres(title)})
            except (httpx.HTTPError,ValueError,TypeError,KeyError):
                current['failures'].append(region+' popular chart unavailable')
        # Learn requested topics from published comments without storing identities/text.
        own=sorted(data.get('videos',{}).items(),key=lambda x:x[1].get('published_at',''),reverse=True)[:3]
        counts=collections.Counter()
        for vid,_ in own:
            try:
                r=client.get(API+'commentThreads',params={'part':'snippet','videoId':vid,'maxResults':20,'order':'relevance','textFormat':'plainText'},headers={'Authorization':'Bearer '+token})
                r.raise_for_status()
                for item in r.json().get('items',[]):
                    text=item['snippet']['topLevelComment']['snippet'].get('textDisplay','')[:1000]
                    if re.search(r'\b(next|more|please|explain|cover|make)\b',text,re.I):
                        counts.update(genres(text))
            except (httpx.HTTPError,KeyError,TypeError,ValueError):
                current['failures'].append('Comment sample unavailable for '+vid)
        current['audience_topic_counts']=dict(counts)
    # Region overlap must not double-count a video in the cross-region summary.
    unique={x['id']:x for x in current['samples']}
    summary={}
    for genre in TOPICS:
        group=[x for x in unique.values() if genre in x['genres']]
        if group:
            summary[genre]={'sample_count':len(group),
                'median_duration_seconds':statistics.median(x['duration'] for x in group),
                'median_views_per_hour':statistics.median(x['views_per_hour'] for x in group)}
    current['genre_signals']=summary
    current['note']='Observational signals, not proof a title or format causes views. Source footage/transcripts are not downloaded.'
    data['research']=current
    print('Daily YouTube research:',len(unique),'unique videos;',len(summary),'matched genres;',len(current['failures']),'unavailable samples')
    return True


def research_signals(data,now):
    research=data.get('research',{})
    try:
        if not 0<=(now-datetime.fromisoformat(research['checked_at'])).total_seconds()<=48*3600:
            return []
    except (KeyError,ValueError,TypeError):return []
    out=[{'title':s['title'],'region':s['region'],'at':research['checked_at'],'source':'YouTube popular chart'} for s in research.get('samples',[]) if s.get('genres')]
    for genre,count in research.get('audience_topic_counts',{}).items():
        if count>=2 and genre in TOPICS:
            out.append({'title':TOPICS[genre][0],'region':'audience','at':research['checked_at'],'source':'aggregate comment topics'})
    return out
