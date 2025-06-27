#!/bin/bash

# 配置参数
FILE="doris.txt"
MARKER="# AUTO-GENERATED CONTENT BELOW"
REPO_DIR=$(pwd)
SYNC_INTERVAL=111
LOG_FILE="sync.log"
BACKUP_DIR="data_backups"

# 初始化环境
init_env() {
    mkdir -p "$BACKUP_DIR"
    if ! grep -q "^$MARKER$" "$FILE"; then
        echo -e "\n$MARKER" >> "$FILE"
        git add "$FILE"
        git commit -m "初始化数据文件标记"
    fi
}

# 数据备份（带时间戳和主机名）
backup_data() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local hostname=$(hostname -s)
    cp "$FILE" "$BACKUP_DIR/${timestamp}_${hostname}.txt"
}

# 安全合并已有数据
merge_existing_data() {
    # 提取当前数据（标记后的内容）
    local current_data=$(grep -A 10000 "^$MARKER$" "$FILE" | grep -v "^$MARKER$")
    
    # 获取远程数据
    git fetch origin
    local remote_data=$(git show origin/master"$FILE" 2>/dev/null | grep -A 10000 "^$MARKER$" | grep -v "^$MARKER$")
    
    # 合并数据（去重）
    # local merged_data=$(echo -e "$current_data\n$remote_data" | sort -u)
    local merged_data=$(echo -e "$current_data\n$remote_data" | awk '!seen[$0]++')

    # 重建文件
    grep -B 10000 "^$MARKER$" "$FILE" | head -n -1 > "$FILE.tmp"
    echo "$MARKER" >> "$FILE.tmp"
    echo "$merged_data" >> "$FILE.tmp"
    
    # 验证合并结果
    if [ $(wc -l < "$FILE.tmp") -gt $(wc -l < "$FILE") ]; then
        backup_data
        mv "$FILE.tmp" "$FILE"
        log "成功合并已有数据，新增 $(( $(wc -l <<< "$merged_data") - $(wc -l <<< "$current_data") )) 行"
        return 0
    else
        log "合并验证失败，保留原文件"
        rm "$FILE.tmp"
        return 1
    fi
}

# 主同步流程
sync_process() {
    cd "$REPO_DIR" || return 1
    
    # 检查本地更改
    if ! git diff --quiet "$FILE"; then
        backup_data
        git add "$FILE"
        git commit -m "自动提交本地更改 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 获取远程更新
    git fetch origin
    
    # 检查是否需要同步
    LOCAL_HEAD=$(git rev-parse @)
    REMOTE_HEAD=$(git rev-parse origin/master)
    
    if [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
        log "无需同步"
        return 0
    fi
    
    # 首次同步特殊处理
    if [ ! -f ".synced" ]; then
        log "首次同步，合并已有数据..."
        if merge_existing_data; then
            touch ".synced"
            git add "$FILE"
            git commit -m "初始合并多服务器数据 $(date '+%Y-%m-%d %H:%M:%S')"
            git push origin master
            return 0
        else
            return 1
        fi
    fi
    
    # 常规同步
    backup_data
    if git merge --no-commit origin/master 2>/dev/null; then
        log "自动合并成功"
        git commit -m "自动合并远程更新 $(date '+%Y-%m-%d %H:%M:%S')"
        git push origin master
    else
        log "检测到冲突，执行智能合并..."
        if resolve_conflict; then
            git add "$FILE"
            git commit -m "解决冲突合并数据 $(date '+%Y-%m-%d %H:%M:%S')"
            git push origin master
        else
            git merge --abort
            log "合并失败，需要手动干预"
            return 1
        fi
    fi
}


resolve_conflict() {
    log "检测到冲突，执行智能合并..."
    
    # 备份当前状态
    cp "$FILE" "$FILE.bak"
    
    # 提取文件各部分
    awk -v marker="$MARKER" '
        BEGIN {print_header=1} 
        $0 == marker {print_header=0; print; print "# Remote data:"; next}
        print_header' "$FILE" > "$FILE.header"
        
    grep -A 10000 "^$MARKER$" "$FILE" | grep -v "^$MARKER$" > "$FILE.local"
    grep -A 10000 "^$MARKER$" "$FILE.conflict" | grep -v "^$MARKER$" > "$FILE.remote"
    
    # 合并文件
    cat "$FILE.header" > "$FILE"
    sort -u "$FILE.local" "$FILE.remote" | grep -v "^#" >> "$FILE"
    
    # 验证合并结果
    if [ ! -s "$FILE" ]; then
        log "合并失败，恢复备份"
        mv "$FILE.bak" "$FILE"
        return 1
    fi
    
    log "合并成功，保留所有数据"
    rm -f "$FILE.header" "$FILE.local" "$FILE.remote" "$FILE.bak"
    return 0
}

# 日志和主循环（同前）
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

main() {
    init_env
    log "启动多服务器数据同步服务"
    
    while true; do
        sync_process
        sleep "$SYNC_INTERVAL"
    done
}

main
