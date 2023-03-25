import rsa
import time, random, string

def starts_with_difficulty_zeros(hashvalue, difficulty):
    i = int.from_bytes(hashvalue, 'big')
    zeroes = 160 - i.bit_length()
    res = zeroes >= difficulty
    return res

for d in range(1,18):
    my_str = str(''.join(random.choices(string.ascii_letters, k=20)))
    start_time = time.time()
    while 1:
        str_hash = rsa.compute_hash(my_str.encode(), 'SHA-1')
        if (starts_with_difficulty_zeros(str_hash, d)):
            end_time = time.time()
            break
        else:
            my_str = str(''.join(random.choices(string.ascii_letters, k=20)))
    print(f'found hash: {str_hash} with {d} zeros in {end_time-start_time} secs')