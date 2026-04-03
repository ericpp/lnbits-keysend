window.PageKeysend = {
  template: '#page-keysend',
  computed: {
    baseUrl() {
      return window.location.origin + '/keysend/api/v1/entries'
    },
    endpoint() {
      return `/keysend/api/v1/settings?usr=${this.g.user.id}`
    }
  },
  data() {
    return {
      settings: [
        {
          type: 'str',
          description: 'Lightning node public key (66-char hex)',
          name: 'node_pubkey'
        }
      ],
      domain: window.location.host,
      entries: [],
      entriesTable: {
        columns: [
          {
            name: 'created_at',
            label: 'Created',
            align: 'left',
            field: 'created_at',
            sortable: true
          },
          {
            name: 'description',
            label: 'Description',
            align: 'left',
            field: 'description'
          },
          {
            name: 'username',
            label: 'Username',
            align: 'left',
            field: 'username',
            sortable: true,
            format: val => val ?? 'None',
            classes: val => (val ? 'text-normal' : 'text-grey')
          },
          {
            name: 'custom_key',
            label: 'Custom Key',
            align: 'left',
            field: 'custom_key'
          },
          {
            name: 'custom_value',
            label: 'Custom Value',
            align: 'left',
            field: 'custom_value'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      formDialog: {
        show: false,
        data: {}
      },
      detailDialog: {
        show: false,
        data: null
      },
      sendDialog: {
        show: false,
        data: {
          destination: '',
          amount: 0,
          custom_key: '',
          custom_value: ''
        }
      }
    }
  },
  methods: {
    wellKnownUrl(entry) {
      const d = entry.domain || window.location.host
      return `https://${d}/.well-known/keysend/${entry.username}`
    },
    mapEntry(obj) {
      obj._data = _.clone(obj)
      obj.created_at = LNbits.utils.formatDate(obj.created_at)
      obj.updated_at = LNbits.utils.formatDate(obj.updated_at)
      return obj
    },
    getEntries() {
      LNbits.api
        .request(
          'GET',
          '/keysend/api/v1/entries?all_wallets=true',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.entries = response.data.map(this.mapEntry)
        })
        .catch(LNbits.utils.notifyApiError)
    },
    closeFormDialog() {
      this.resetFormData()
    },
    openDetailDialog(entryId) {
      var entry = _.findWhere(this.entries, {id: entryId})
      this.detailDialog.data = {
        id: entry.id,
        description: entry.description,
        custom_key: entry.custom_key,
        custom_value: entry.custom_value,
        webhook: entry.webhook_url || 'none',
        username: entry.username,
        domain: entry.domain
      }
      this.detailDialog.show = true
    },
    openUpdateDialog(entryId) {
      const entry = _.findWhere(this.entries, {id: entryId})
      this.formDialog.data = {...entry}
      this.formDialog.show = true
    },
    sendFormData() {
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })
      const data = _.clone(this.formDialog.data)
      if (data.id) {
        this.updateEntry(wallet, data)
      } else {
        this.createEntry(wallet, data)
      }
    },
    resetFormData() {
      this.formDialog = {
        show: false,
        data: {}
      }
    },
    updateEntry(wallet, data) {
      LNbits.api
        .request(
          'PUT',
          '/keysend/api/v1/entries/' + data.id,
          wallet.adminkey,
          data
        )
        .then(response => {
          this.entries = _.reject(this.entries, obj => obj.id === data.id)
          this.entries.push(this.mapEntry(response.data))
          this.formDialog.show = false
          this.resetFormData()
        })
        .catch(LNbits.utils.notifyApiError)
    },
    createEntry(wallet, data) {
      LNbits.api
        .request('POST', '/keysend/api/v1/entries', wallet.adminkey, data)
        .then(response => {
          this.getEntries()
          this.formDialog.show = false
          this.resetFormData()
        })
        .catch(LNbits.utils.notifyApiError)
    },
    deleteEntry(entryId) {
      var entry = _.findWhere(this.entries, {id: entryId})
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this keysend entry?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/keysend/api/v1/entries/' + entryId,
              _.findWhere(this.g.user.wallets, {id: entry.wallet}).adminkey
            )
            .then(() => {
              this.entries = _.reject(this.entries, obj => obj.id === entryId)
            })
            .catch(LNbits.utils.notifyApiError)
        })
    },
    openSendDialog() {
      this.sendDialog.show = true
    },
    sendKeysend() {
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.sendDialog.data.wallet
      })
      if (!wallet) {
        LNbits.utils.notifyApiError({message: 'Please select a wallet'})
        return
      }
      const payload = {
        destination: this.sendDialog.data.destination,
        amount: parseInt(this.sendDialog.data.amount)
      }
      if (this.sendDialog.data.custom_key && this.sendDialog.data.custom_value) {
        payload.custom_records = {}
        payload.custom_records[this.sendDialog.data.custom_key] =
          this.sendDialog.data.custom_value
      }
      LNbits.api
        .request('POST', '/keysend/api/v1/send', wallet.adminkey, payload)
        .then(response => {
          this.$q.notify({
            type: 'positive',
            message: 'Keysend sent successfully!'
          })
          this.sendDialog.show = false
          this.sendDialog.data = {
            destination: '',
            amount: 0,
            custom_key: '',
            custom_value: '',
            wallet: null
          }
        })
        .catch(LNbits.utils.notifyApiError)
    }
  },
  created() {
    if (this.g.user.wallets?.length) {
      this.getEntries()
    }
  }
}
