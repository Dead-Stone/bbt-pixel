"""Original line banks for the offline mock brain.  Templates: {o} addressee, {place}, {time}, {mem} a recent
memory phrase, {food}.  Nothing here quotes the TV series; these are written for this project."""

OPEN = {
 'sheldon': ["{o}. You are {late} minutes off your usual position. I noticed.", "For the record, {o}, I was about to start a conversation myself.",
             "Ah, {o}. I have prepared three topics, ranked by importance.", "Technically this counts as our scheduled small talk, {o}."],
 'leonard': ["Hey {o}, got a second?", "Oh, hi {o}. How's your day going so far?", "{o}! Perfect timing, I need a sanity check.", "Hey. You look like you have news, {o}."],
 'penny': ["Hey sweetie, what's up?", "{o}! Okay, talk to me, I need a break.", "Hi hon. You look like you're overthinking something.", "Oh good, {o}, a normal human. Hi."],
 'howard': ["{o}, my friend! Ask me what I built this morning.", "Well, if it isn't {o}. Hold that thought, I'm about to be impressive.", "{o}! Engineering update, very exciting, try to keep up.", "Hey {o}, quick question, zero theory involved."],
 'raj': ["{o}! Oh, it's like a comet showing up right on schedule.", "Hey {o}, you have to hear about my morning.", "{o}, hi! Okay, I'll talk slower this time.", "Namaste, {o}. Got a minute for a fun fact?"],
 'bernadette': ["Hiii {o}! Quick thing, and then you're going to do what I say.", "{o}, sweetie! How are you? Good. Now listen.", "Oh, {o}, perfect. I need a second opinion that agrees with me.", "Hey {o}! Did you eat? You should eat."],
 'amy': ["Hello, {o}. My amygdala registered your arrival as a positive event.", "{o}! Best-friend status check: we're still best friends, correct?", "Greetings, {o}. I'm conducting a casual-conversation trial. You're in it.", "{o}. I have a hypothesis about your day."],
}
REPLY = {
 'sheldon': ["That is incorrect, but in an interesting way.", "I'll allow it, with a footnote.", "Your reasoning has a hole you could drive a rover through.", "Fascinating. Unhelpful, but fascinating.", "I calculate a sixty-two percent chance you're joking.", "Noted. I've filed that under 'Mildly Relevant'."],
 'leonard': ["Okay, okay, fair point.", "Ha. Yeah, that tracks.", "I'm not saying you're wrong. I'm saying I'm tired.", "Honestly? Same.", "That's... actually a good idea.", "Let's not make this a whole thing."],
 'penny': ["Uh-huh. And in English?", "Sweetie, I love you, but no.", "Okay, that's kind of adorable.", "Wow. Okay. Moving on.", "Fine, you win this one.", "Ha! Totally called it."],
 'howard': ["Classic theorist move.", "See, that's why they give the hard stuff to engineers.", "Zing. I'll be here all week.", "Respectfully, my robot disagrees.", "I've done harder things in a clean room wearing mittens.", "Ooh, now we're talking."],
 'raj': ["That's beautiful, like a binary star system.", "Oh my god, yes, exactly!", "Dude, that's the nicest thing anyone's said all week.", "Okay, now I'm emotional.", "Wait, wait, I have a metaphor for this.", "Ha, cosmic."],
 'bernadette': ["Aww. No.", "Cute. Now do it properly.", "Honey, I've cultured nicer things than that idea.", "Ha! Okay, that's funny.", "We are not doing that.", "Sure, if you want to be wrong."],
 'amy': ["My prefrontal cortex finds that compelling.", "Noted for my field journal.", "As a scientist and your friend, I disagree.", "That released a measurable amount of dopamine.", "Interesting. Repeat it slower.", "Agreed. Wholeheartedly. Clinically."],
}
CLOSE = {
 'sheldon': ["This conversation has reached its natural conclusion.", "I have to go; my schedule is not a suggestion.", "Goodbye. I'll send a summary."],
 'leonard': ["Okay, I should get back to it.", "Talk later? Cool.", "Alright, I'm gonna go before Sheldon finds me."],
 'penny': ["Okay, love you, bye.", "Gotta run, hon.", "Alright, I'm out. Behave."],
 'howard': ["And scene. Thank you, thank you.", "Gotta go, the robot misses me.", "Later, buddy."],
 'raj': ["Okay bye, this was lovely!", "I'll text you a star chart.", "See you later, space cowboy."],
 'bernadette': ["Okay! Bye! Do what I said.", "Byeee. Love you. Don't be late.", "Alright, I've got cultures to boss around."],
 'amy': ["Farewell. This interaction was a success.", "I'll log this as a bonding event.", "Goodbye. I'm already looking forward to the debrief."],
}
TOPIC = {
 'work': {
  'sheldon': ["My calculation is ninety-eight percent elegant and two percent Leonard's coffee stain.", "I have proven that the problem is hard. That counts as progress."],
  'leonard': ["The laser drifted again, so I spent an hour realigning mirrors.", "I think the detector works. I'm scared to touch it."],
  'penny': ["Table six asked if the cheesecake was gluten-free. It's cheesecake.", "I had a callback for a commercial. A yogurt commercial, but still."],
  'howard': ["The robot arm can pick up an egg now. Mostly without crushing it.", "The rover drove straight for ten whole metres. Applause welcome."],
  'raj': ["I found a variable star that flickers like it's nervous. Relatable.", "My data finally reduced. It looks like a smudge, but a significant smudge."],
  'bernadette': ["My cultures are growing beautifully. That's a threat to someone, somewhere.", "I got the quarterly numbers in early. Everyone's terrified of me. It's great."],
  'amy': ["The neurons I'm imaging fired in a pattern that resembled a smile.", "I'm borrowing this bench until someone in physics notices. So, indefinitely."]},
 'lunch': {
  'sheldon': ["Today is the day I have the soup. The soup is the reason the day has structure.", "The tray system here is suboptimal, but predictable. I respect that."],
  'leonard': ["Is it just me or is the mystery casserole getting more mysterious?", "I grabbed extra napkins. Don't ask why, just trust me."],
  'penny': ["You guys eat here every day? Brave.", "I'm stealing a fry. Consider it a tip."],
  'howard': ["I rate this pudding three stars. One for texture, two for trying.", "Fun fact, astronauts would trade a lot for this salad bar."],
  'raj': ["This curry is lying to itself, but I respect the confidence.", "If you squint, the jello looks like a nebula."],
  'bernadette': ["Howard, eat a vegetable. That's not a suggestion.", "I came all the way across town for this lunch date. Smile."],
  'amy': ["Sharing a meal releases oxytocin. I brought extra crackers to maximise it.", "Sheldon, I sat on your preferred side. Growth."]},
 'dinner': {
  'sheldon': ["I'll have my usual. Do not improvise, Penny.", "The booth acoustics are acceptable this evening."],
  'leonard': ["Penny's working, so tip like we mean it.", "Friday dinner here is the one tradition I actually like."],
  'penny': ["Okay, nerds, who's getting what? And no, we don't have a 'theoretical special'.", "If anyone sends food back, I'm telling everyone your middle names."],
  'howard': ["Penny, could you ask the chef to make it extra crispy? Like a heat shield.", "I'll split the appetizer, but I get the strategic half."],
  'raj': ["This place is my favourite constellation of flavours.", "I'm ordering dessert first. Life is short, stars are long."],
  'bernadette': ["Nobody touch the bread before I say grace. Kidding! Mostly.", "Let's order quickly, I have plans to destroy you all at game night."],
  'amy': ["Dining with friends on a Friday. Adolescent me would be stunned.", "Penny, as your best friend, I'll take the large slice."]},
 'gamenight': {
  'sheldon': ["The rules are on the whiteboard. Read them twice.", "I am not competitive. I simply prefer the outcome where I win."],
  'leonard': ["Alright, teams. And Sheldon, you're not allowed to be on a team with yourself.", "Who brought snacks? Raj, I love you."],
  'penny': ["I don't know the rules, but I'm going to win anyway.", "Let's make it interesting: losers do the dishes."],
  'howard': ["I made a new expansion deck. It's balanced. Totally balanced.", "Strategy tip: never trust a physicist with the dice."],
  'raj': ["I made samosa bites shaped like planets!", "If I lose, I'm lying down on the floor for a while."],
  'bernadette': ["Sweet reminder: I don't lose at games.", "Howard, sit. You're my partner and we are winning."],
  'amy': ["I've studied everyone's tells. Leonard blinks when he bluffs.", "Sheldon and I are an unbeatable dyad."]},
 'science': {
  'sheldon': ["String theory is not stuck. It's resting.", "Engineering is just physics wearing a hard hat."],
  'leonard': ["Experimentalists do the real work. I'll say it.", "The interferometer is basically a very expensive mood ring."],
  'penny': ["So it's like... space, but smaller?", "Explain it like I'm auditioning for a toothpaste ad."],
  'howard': ["Theory is nice until you need it to survive launch vibrations.", "I put a sensor on the coffee machine. It's sad data."],
  'raj': ["Did you know some stars wander alone through the galaxy? Rogue stars. Like me before you guys.", "There's a galaxy shaped like a sombrero. Science is fun."],
  'bernadette': ["The bacteria in your kitchen sponge would astonish you. And not in a good way.", "Microbes are just tiny co-workers who never complain."],
  'amy': ["Boredom is your brain asking for novelty. Mine is asking for Sheldon.", "I mapped a monkey's response to cheese. Very similar to Penny's."]},
 'plans': {
  'sheldon': ["Leonard drives at 8:10. We leave at 8:10 exactly, not 'around'.", "Tonight: dinner, then game night. The schedule has been laminated."],
  'leonard': ["We're doing The Amber Slice at quarter to seven, right?", "I'll drive. Sheldon, you're not touching the radio."],
  'penny': ["Shift starts at half two, so whatever you want from me, ask now.", "After work I'm coming over. Save me a spot that isn't Sheldon's."],
  'howard': ["Bernie's meeting me for lunch. Act cool.", "I'll bring the new expansion tonight. Prepare."],
  'raj': ["I can host next week! I'm planning a theme.", "I'll get a ride with Leonard. Unless I drive. I'll drive."],
  'bernadette': ["Lunch with Howard at noon, dinner at the Slice, then I crush everyone.", "I'll be there at 6:40. If you're late, I'll know."],
  'amy': ["Our relationship agreement allows for a seated dinner on Fridays.", "Penny and I have scheduled spontaneous fun for Saturday."]},
 'memory': {
  'sheldon': ["Earlier I observed {mem}. I have questions.", "I noted that {mem}. Statistically unusual."],
  'leonard': ["I saw that {mem}. Everything okay?", "Wait, earlier {mem}? Huh."],
  'penny': ["Okay, so I noticed {mem}. Spill.", "Not to be nosy, but {mem}."],
  'howard': ["Little bird told me {mem}. The bird was me.", "Saw that {mem}. Smooth."],
  'raj': ["I noticed {mem}, and I've been thinking about it all day!", "Earlier, {mem}. That's so you."],
  'bernadette': ["I saw {mem}. We'll talk about that.", "So, {mem}? Interesting choice."],
  'amy': ["I observed that {mem}. I've added it to my notes.", "Earlier, {mem}. I found that endearing."]},
 'commute': {
  'sheldon': ["Leonard, signal earlier. The car behind us had feelings about it.", "LOS ROBLES AV traffic has a pattern. I'm close to cracking it."],
  'leonard': ["Traffic on LOS ROBLES AV was not my fault.", "Ten minutes to campus, if nobody asks for a detour."],
  'penny': ["My car's making the noise again. Don't look at me like that.", "Walking to the Slice. My cardio for the day."],
  'howard': ["I could build a faster car. I just choose not to.", "I parked right by the quad. Like a winner."],
  'raj': ["I drove! I only missed one turn.", "The street smells like jasmine tonight. Romantic."],
  'bernadette': ["I made it across town in record time. Don't ask how.", "Howard, you're driving home. I'm resting my competitive spirit."],
  'amy': ["I took the bus and observed eleven distinct human behaviours.", "Commuting gives me time to rehearse friendly conversations."]},
}
FOOD = ['the takeout', 'a burrito', 'pad thai', 'cheesecake', 'the soup of the day', 'cereal']
