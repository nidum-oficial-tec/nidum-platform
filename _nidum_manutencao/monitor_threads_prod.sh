#!/bin/sh
# Monitor de rajadas de threads do PID 1 (ChatND). Roda em background dentro do container.
# A cada INTERVALO s: conta /proc/1/task e grava. Quando o numero SOBE, tira py-spy dump
# na hora (quem esta ativo em Python = o call site) e guarda os tids novos.
D=/tmp/mon
INTERVALO=${INTERVALO:-5}
mkdir -p "$D"
ls /proc/1/task | sort -n > "$D/tids.prev"
ultimo=$(wc -l < "$D/tids.prev")
echo "$(date -u +%FT%TZ) inicio threads=$ultimo pid=$$" >> "$D/monitor.out"
while :; do
  n=$(ls /proc/1/task | wc -l)
  mem=$(cat /sys/fs/cgroup/memory.current 2>/dev/null)
  echo "$(date -u +%FT%TZ) $n $mem" >> "$D/threads.log"
  if [ "$n" -gt "$ultimo" ]; then
    ts=$(date -u +%Y%m%dT%H%M%SZ)
    # 1) quem esta rodando em Python NESTE instante
    py-spy dump --pid 1 > "$D/burst_${ts}.pyspy" 2>&1
    # 2) tids novos
    ls /proc/1/task | sort -n > "$D/tids.now"
    grep -vxFf "$D/tids.prev" "$D/tids.now" > "$D/burst_${ts}.tids"
    echo "$(date -u +%FT%TZ) RAJADA $ultimo -> $n (+$((n-ultimo))) mem=$mem" >> "$D/monitor.out"
  fi
  if [ "$n" -ne "$ultimo" ]; then
    ls /proc/1/task | sort -n > "$D/tids.prev"
  fi
  ultimo=$n
  sleep "$INTERVALO"
done
