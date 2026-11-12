#!/usr/bin/env bash
# Creates Peheraav's server on Azure for Students (no credit card), using only free-eligible pieces:
#   a B2ats_v2 (or B1s) Ubuntu 24.04 server, a 64 GB Premium SSD (P6), a public IP, and firewall
#   rules for SSH (22), HTTP (80) and HTTPS (443). No auto-shutdown.
# Student subscriptions may only use some regions; this asks Azure which, and tries the closest first.
#
# Run it in Azure Cloud Shell (Bash), with your laptop's PUBLIC ssh key:
#   bash azure-create-vm.sh "ssh-ed25519 AAAA... peheraav-azure-server"
set -uo pipefail

PUBKEY="${1:-}"
[ -n "$PUBKEY" ] || { echo "Give your public SSH key in quotes as the first argument."; exit 1; }
RG=peheraav-rg
NAME=peheraav

ALLOWED=$(az policy assignment list --disable-scope-strict-match \
  --query "[].parameters.listOfAllowedLocations.value[]" -o tsv 2>/dev/null | tr '[:upper:]' '[:lower:]' | sort -u)
echo "Regions your subscription may use: $(echo "$ALLOWED" | tr '\n' ' ')"
PREFER="indiasouthcentral centralindia southindia westindia southeastasia malaysiawest eastasia uaenorth japaneast koreacentral australiaeast northeurope westeurope uksouth eastus eastus2 centralus westus2"
TRY=""
for r in $PREFER; do echo "$ALLOWED" | grep -qx "$r" && TRY="$TRY $r"; done
[ -n "$TRY" ] || TRY="$ALLOWED"
[ -n "$TRY" ] || TRY="centralindia southeastasia"
echo "Will try, in order:$TRY"

az group create --name "$RG" --location "$(echo $TRY | awk '{print $1}')" --output none || exit 1

for LOC in $TRY; do
  for SIZE in Standard_B2ats_v2 Standard_B1s; do
    echo; echo "==> Trying $SIZE in $LOC"
    # Each attempt gets its own network names, so a failed try never gets in the way of the next.
    if az vm create \
        --resource-group "$RG" --name "$NAME" --location "$LOC" \
        --image Canonical:ubuntu-24_04-lts:server:latest --size "$SIZE" \
        --admin-username azureuser --ssh-key-values "$PUBKEY" \
        --os-disk-size-gb 64 --storage-sku Premium_LRS \
        --vnet-name "peheraav-vnet-$LOC" --subnet default --nsg "peheraav-nsg-$LOC" \
        --public-ip-address "peheraav-ip-$LOC" --public-ip-sku Standard --nsg-rule SSH \
        --os-disk-delete-option Delete --nic-delete-option Delete \
        --output none 2>/tmp/peheraav-vm-err.txt; then
      az vm open-port --resource-group "$RG" --name "$NAME" --port 80,443 --priority 1010 --output none
      IP=$(az vm show -d --resource-group "$RG" --name "$NAME" --query publicIps -o tsv)
      echo
      echo "=================================================="
      echo " Done! Size: $SIZE   Region: $LOC"
      echo " Public IP: $IP"
      echo " Free web address (pick a name, letters/digits/hyphens):"
      echo "   az network public-ip update -g $RG -n peheraav-ip-$LOC --dns-name YOUR-NAME --query dnsSettings.fqdn -o tsv"
      echo "=================================================="
      exit 0
    fi
    grep -oE "(RequestDisallowedByAzure|SkuNotAvailable|QuotaExceeded|OperationNotAllowed)[^.]*" /tmp/peheraav-vm-err.txt | head -1
    az vm delete --resource-group "$RG" --name "$NAME" --yes --output none 2>/dev/null || true
  done
done
echo "Couldn't create the server in any allowed region. Send the lines above."
exit 1
