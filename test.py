import rsa
import time

def starts_with_difficulty_zeros(next_hash, difficulty):
    next_hash = int.from_bytes(next_hash, "big")   
    mask = (1<<(160-difficulty))-1
    mask &= next_hash
    res = next_hash^mask == 0
    return res

d = 1

for d in range(10):
    my_str = "1"
    start_time = time.time()
    while 1:
        str_hash = rsa.compute_hash(my_str.encode(), 'SHA-1')
        if (starts_with_difficulty_zeros(str_hash, d)):
            end_time = time.time()
            break
        else:
            my_str = str(int(my_str)+1)
    print(f'found hash: {str_hash} with {d} zeros in {end_time-start_time} secs')