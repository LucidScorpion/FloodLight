#!/usr/bin/env python
# Copyright (c) 2017 @YourRav3nSec
#
# 
import re, os, sys
from time import sleep
import certstream
import tqdm
import entropy
from tld import get_tld
from Levenshtein import distance
from termcolor import colored, cprint


from suspicious import keywords, tlds

os.system("pip install colored")

sleep(1)
if not os.geteuid() == 0:
	sys.exit('Script must be run as root')
	

os.system('cls' if os.name == 'nt' else 'clear')


print ("""
~~=[ FloodLight - WebScanner
~~=[ v1.0 - 'Blackvortex'
~~=[ coders: @YourRav3nSec
~~=[ https://twitter.com/YourRav3nSec
~~=[ #OpPedo #OpDeathEaters #Rav3nSec
""")
sleep(5)

log_suspicious = 'suspicious_domains.log'

pbar = tqdm.tqdm(desc='certificate_update', unit='cert')

def score_domain(domain):
    """Score `domain`.
    The highest score, the most probable `domain` is a pedo site.
    Args:
        domain (str): the domain to check.
    Returns:
        int: the score of `domain`.
    """
    score = 0
    for t in tlds:
        if domain.endswith(t):
            score += 20

    # Remove initial '*.' for wildcard certificates bug
    if domain.startswith('*.'):
        domain = domain[2:]

    # Removing TLD to catch inner TLD in subdomain (ie. paypal.com.domain.com)
    try:
        res = get_tld(domain, as_object=True, fail_silently=True, fix_protocol=True)
        domain = '.'.join([res.subdomain, res.domain])
    except:
        pass

    words_in_domain = re.split("\W+", domain)

    # Remove initial '*.' for wildcard certificates bug
    if domain.startswith('*.'):
        domain = domain[2:]
        # ie. detect fake .com (ie. *.com-account-management.info)
        if words_in_domain[0] in ['com', 'net', 'org']:
            score += 10

    # Testing keywords
    for word in keywords.keys():
        if word in domain:
            score += keywords[word]

    # Higer entropy is kind of suspicious
    score += int(round(entropy.shannon_entropy(domain)*50))

    # Testing Levenshtein distance for strong keywords (>= 70 points) (ie. paypol)
    for key in [k for (k,s) in keywords.items() if s >= 70]:
        # Removing too generic keywords (ie. mail.domain.com)
        for word in [w for w in words_in_domain if w not in ['email', 'mail', 'cloud']]:
            if distance(str(word), str(key)) == 1:
                score += 70

    # Lots of '-' (ie. www.paypal-datacenter.com-acccount-alert.com)
    if 'xn--' not in domain and domain.count('-') >= 4:
        score += domain.count('-') * 3

    # Deeply nested subdomains (ie. www.paypal.com.security.accountupdate.gq)
    if domain.count('.') >= 3:
        score += domain.count('.') * 3

    return score


def callback(message, context):
    """Callback handler for certstream events."""
    if message['message_type'] == "heartbeat":
        return

    if message['message_type'] == "certificate_update":
        all_domains = message['data']['leaf_cert']['all_domains']

        for domain in all_domains:
            pbar.update(1)
            score = score_domain(domain.lower())

            # If issued from a free CA = more suspicious
            if "Let's Encrypt" in message['data']['chain'][0]['subject']['aggregated']:
                score += 10

            if score >= 100:
                tqdm.tqdm.write(
                    "[!] Suspicious: "
                    "{} (score={})".format(colored(domain, 'red', attrs=['underline', 'bold']), score))
            elif score >= 90:
                tqdm.tqdm.write(
                    "[!] Suspicious: "
                    "{} (score={})".format(colored(domain, 'red', attrs=['underline']), score))
            elif score >= 80:
                tqdm.tqdm.write(
                    "[!] Likely    : "
                    "{} (score={})".format(colored(domain, 'yellow', attrs=['underline']), score))
            elif score >= 65:
                tqdm.tqdm.write(
                    "[+] Potential : "
                    "{} (score={})".format(colored(domain, attrs=['underline']), score))

            if score >= 65:
                with open(log_suspicious, 'a') as f:
                    f.write("{}\n".format(domain))


certstream.listen_for_events(callback)
