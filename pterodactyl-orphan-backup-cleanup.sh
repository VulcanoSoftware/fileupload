#!/bin/bash
#
# Pterodactyl Orphaned Backup Cleanup
# Verwijdert database-entries waarvan het .tar.gz bestand niet meer bestaat.
#
# Gebruik:
#   DRY_RUN=1 ./pterodactyl-orphan-backup-cleanup.sh   # alleen tonen (veilig)
#   DRY_RUN=0 ./pterodactyl-orphan-backup-cleanup.sh   # echt verwijderen
#

set -euo pipefail

# ==================== CONFIG ====================
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-pterodactyl}"
DB_PASS="${DB_PASS:-}"                    # zet hier je wachtwoord, of gebruik .my.cnf
DB_NAME="${DB_NAME:-panel}"

BACKUP_DIR="${BACKUP_DIR:-/var/lib/pterodactyl/backups}"
LOG_FILE="${LOG_FILE:-/var/log/pterodactyl-orphan-backup-cleanup.log}"

# 1 = alleen tonen, 0 = echt verwijderen
DRY_RUN="${DRY_RUN:-1}"
# ================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# MariaDB client (ondersteunt ook mysql)
MYSQL_CMD=(mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER")
if [[ -n "$DB_PASS" ]]; then
    MYSQL_CMD+=(-p"$DB_PASS")
fi
MYSQL_CMD+=("$DB_NAME" -N -B)

log "=== Start orphaned backup cleanup (DRY_RUN=$DRY_RUN) ==="

if [[ ! -d "$BACKUP_DIR" ]]; then
    log "ERROR: Backup directory bestaat niet: $BACKUP_DIR"
    exit 1
fi

# Alleen lokale (wings) backups die succesvol zijn en niet soft-deleted
# We negeren is_locked = 1 uit voorzorg
QUERY="
SELECT uuid, id, name, server_id
FROM backups
WHERE disk = 'wings'
  AND deleted_at IS NULL
  AND is_locked = 0
  AND is_successful = 1
"

mapfile -t ROWS < <("${MYSQL_CMD[@]}" -e "$QUERY" 2>/dev/null || true)

if [[ ${#ROWS[@]} -eq 0 ]]; then
    log "Geen lokale backups gevonden in de database."
    exit 0
fi

REMOVED=0
CHECKED=0

for row in "${ROWS[@]}"; do
    # uuid | id | name | server_id
    uuid=$(echo "$row" | cut -f1)
    id=$(echo "$row" | cut -f2)
    name=$(echo "$row" | cut -f3)
    server_id=$(echo "$row" | cut -f4)

    file="$BACKUP_DIR/${uuid}.tar.gz"
    CHECKED=$((CHECKED + 1))

    if [[ -f "$file" ]]; then
        continue
    fi

    # Bestand bestaat niet meer → orphan
    log "ORPHAN gevonden: id=$id uuid=$uuid name=\"$name\" server_id=$server_id"

    if [[ "$DRY_RUN" == "1" ]]; then
        log "  [DRY-RUN] zou DELETE FROM backups WHERE id = $id uitvoeren"
    else
        "${MYSQL_CMD[@]}" -e "DELETE FROM backups WHERE id = $id AND disk = 'wings' LIMIT 1;"
        log "  Verwijderd uit database (id=$id)"
        REMOVED=$((REMOVED + 1))
    fi
done

log "Klaar. Gecontroleerd: $CHECKED | Orphans verwijderd: $REMOVED (DRY_RUN=$DRY_RUN)"
log "=== Einde ==="
