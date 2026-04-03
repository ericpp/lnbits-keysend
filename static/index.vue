<template id="page-keysend">
  <div class="row q-col-gutter-md">
    <div class="col-12 col-md-7 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <q-btn unelevated color="primary" @click="formDialog.show = true"
            >New keysend address</q-btn
          >
          <q-btn
            unelevated
            color="secondary"
            class="q-ml-sm"
            @click="openSendDialog()"
            >Send keysend</q-btn
          >
        </q-card-section>
      </q-card>

      <q-card>
        <q-card-section>
          <q-tabs
            v-model="activeTab"
            dense
            class="text-grey"
            active-color="primary"
            indicator-color="primary"
            align="left"
            narrow-indicator
          >
            <q-tab name="addresses" label="Addresses"></q-tab>
            <q-tab name="payments" label="Received Payments"></q-tab>
          </q-tabs>
          <q-separator></q-separator>

          <q-tab-panels v-model="activeTab" animated>
            <q-tab-panel name="addresses">
              <q-table
                dense
                flat
                :rows="entries"
                :columns="entriesTable.columns"
                row-key="id"
                v-model:pagination="entriesTable.pagination"
              >
                <template v-slot:header="props">
                  <q-tr class="text-left" :props="props">
                    <q-th auto-width></q-th>
                    <q-th
                      v-for="col in props.cols"
                      :key="col.name"
                      :props="props"
                    >
                      <span v-text="col.label"></span>
                    </q-th>
                    <q-th auto-width></q-th>
                  </q-tr>
                </template>
                <template v-slot:body="props">
                  <q-tr :props="props">
                    <q-td auto-width>
                      <q-btn
                        dense
                        size="xs"
                        icon="visibility"
                        :color="$q.dark.isActive ? 'grey-7' : 'grey-5'"
                        class="q-ml-sm"
                        @click="openDetailDialog(props.row.id)"
                        ><q-tooltip>View Details</q-tooltip></q-btn
                      >
                      <q-btn
                        flat
                        dense
                        size="xs"
                        @click="openUpdateDialog(props.row.id)"
                        icon="edit"
                        color="light-blue"
                        class="q-ml-sm"
                      >
                        <q-tooltip>Edit</q-tooltip>
                      </q-btn>
                      <q-btn
                        flat
                        dense
                        size="xs"
                        @click="deleteEntry(props.row.id)"
                        icon="cancel"
                        color="pink"
                        class="q-ml-sm"
                        ><q-tooltip>Delete</q-tooltip></q-btn
                      >
                    </q-td>
                    <q-td
                      v-for="col in props.cols"
                      :key="col.name"
                      :props="props"
                      v-text="col.value"
                    ></q-td>
                    <q-td>
                      <q-icon
                        v-if="props.row.webhook_url"
                        size="14px"
                        name="http"
                      >
                        <q-tooltip
                          >Webhook to
                          <span v-text="props.row.webhook_url"></span
                        ></q-tooltip>
                      </q-icon>
                    </q-td>
                  </q-tr>
                </template>
              </q-table>
            </q-tab-panel>

            <q-tab-panel name="payments">
              <q-table
                dense
                flat
                :rows="receivedPayments"
                :columns="receivedTable.columns"
                row-key="payment_hash"
                v-model:pagination="receivedTable.pagination"
              >
                <template v-slot:header="props">
                  <q-tr class="text-left" :props="props">
                    <q-th
                      v-for="col in props.cols"
                      :key="col.name"
                      :props="props"
                    >
                      <span v-text="col.label"></span>
                    </q-th>
                  </q-tr>
                </template>
                <template v-slot:body="props">
                  <q-tr :props="props">
                    <q-td
                      v-for="col in props.cols"
                      :key="col.name"
                      :props="props"
                      v-text="col.value"
                    ></q-td>
                  </q-tr>
                </template>
                <template v-slot:no-data>
                  <div class="full-width row flex-center text-grey q-gutter-sm">
                    <span>No keysend payments received yet.</span>
                  </div>
                </template>
              </q-table>
            </q-tab-panel>
          </q-tab-panels>
        </q-card-section>
      </q-card>
    </div>

    <div class="col-12 col-md-5 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6 class="text-subtitle1 q-my-none">Keysend extension</h6>
        </q-card-section>
        <q-card-section class="q-pa-none">
          <q-separator></q-separator>
          <q-list>
            <q-expansion-item
              group="extras"
              icon="swap_vertical_circle"
              label="API info"
              :content-inset-level="0.5"
            >
              <q-btn
                flat
                label="Swagger API"
                type="a"
                href="../docs#/keysend"
              ></q-btn>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                label="List keysend addresses"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-blue">GET</span>
                      /keysend/api/v1/entries</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;invoice_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 200 OK (application/json)
                    </h5>
                    <code>[&lt;keysend_address_object&gt;, ...]</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X GET <span v-text="baseUrl"></span> -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].inkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                label="Create a keysend address"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-green">POST</span>
                      /keysend/api/v1/entries</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;admin_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Body (application/json)
                    </h5>
                    <code
                      >{"description": &lt;string&gt;, "username":
                      &lt;string&gt;, "custom_key": &lt;string&gt;,
                      "custom_value": &lt;string&gt;}</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 201 CREATED (application/json)
                    </h5>
                    <code>&lt;keysend_address_object&gt;</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X POST <span v-text="baseUrl"></span> -d
                      '{"description": "my address", "username": "alice",
                      "custom_key": "696969", "custom_value": "55"}' -H
                      "Content-type: application/json" -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].adminkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                label="Send keysend payment"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-green">POST</span>
                      /keysend/api/v1/send</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;admin_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Body (application/json)
                    </h5>
                    <code
                      >{"destination": &lt;pubkey_hex&gt;, "amount":
                      &lt;integer_sats&gt;, "custom_records": {"696969":
                      "55"}}</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 200 OK (application/json)
                    </h5>
                    <code>{"payment_hash": &lt;string&gt;, "status": "ok"}</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X POST
                      <span
                        v-text="baseUrl.replace('/entries', '/send')"
                      ></span>
                      -d '{"destination": "02abc...", "amount": 100,
                      "custom_records": {"696969": "55"}}' -H "Content-type:
                      application/json" -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].adminkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                label="Delete a keysend address"
                class="q-pb-md"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-pink">DELETE</span>
                      /keysend/api/v1/entries/&lt;entry_id&gt;</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;admin_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 200 OK
                    </h5>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X DELETE
                      <span
                        v-text="baseUrl + '/&lt;entry_id&gt;'"
                      ></span>
                      -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].adminkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-expansion-item>
            <q-separator></q-separator>
            <q-expansion-item
              group="extras"
              icon="info"
              label="About Keysend"
            >
              <q-card>
                <q-card-section>
                  <p>
                    Keysend (spontaneous payments) allows sending payments
                    directly to a Lightning node's public key without requiring
                    an invoice. Custom TLV records (customKey/customValue) are
                    used to route payments to specific recipients, commonly used
                    in Value4Value / podcasting apps.
                  </p>
                  <p>
                    The <code>/.well-known/keysend/{username}</code> endpoint
                    enables discovery of keysend payment details, returning the
                    node pubkey and custom TLV data needed to send payments to a
                    specific user.
                  </p>
                </q-card-section>
              </q-card>
            </q-expansion-item>
          </q-list>
        </q-card-section>
      </q-card>
    </div>

    <!-- Create / Update dialog -->
    <q-dialog v-model="formDialog.show" @hide="closeFormDialog">
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card">
        <q-form @submit="sendFormData" class="q-gutter-md">
          <q-select
            filled
            dense
            emit-value
            v-model="formDialog.data.wallet"
            :options="g.user.walletOptions"
            label="Wallet *"
          >
          </q-select>
          <q-input
            filled
            dense
            v-model.trim="formDialog.data.description"
            type="text"
            label="Description *"
          >
          </q-input>
          <div class="row">
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.username"
                type="text"
                label="Username (for well-known)"
                @input="
                  formDialog.data.username =
                    formDialog.data.username.toLowerCase()
                "
              />
            </div>
            <div class="col" style="flex: 0 0 auto; margin-top: 10px">
              <span class="label"> &nbsp;@&nbsp; </span>
            </div>
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.domain"
                type="text"
                :label="domain"
              />
            </div>
          </div>
          <div class="row q-col-gutter-sm">
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.custom_key"
                type="text"
                label="Custom Key *"
                hint="TLV record key (e.g. 696969)"
              >
              </q-input>
            </div>
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.custom_value"
                type="text"
                label="Custom Value *"
                hint="TLV record value (unique identifier)"
              >
              </q-input>
            </div>
          </div>
          <q-expansion-item
            group="advanced"
            icon="settings"
            label="Advanced options"
          >
            <q-card>
              <q-card-section>
                <div class="row">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_url"
                      type="text"
                      label="Webhook URL (optional)"
                      hint="URL called when this address receives a keysend payment."
                    ></q-input>
                  </div>
                </div>
                <div class="row" v-if="formDialog.data.webhook_url">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_headers"
                      type="text"
                      label="Webhook headers (optional)"
                      hint="Custom headers as JSON string."
                    ></q-input>
                  </div>
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_body"
                      type="text"
                      label="Webhook custom data (optional)"
                      hint="Custom body data as JSON string."
                    ></q-input>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </q-expansion-item>
          <div class="row q-mt-lg">
            <q-btn
              v-if="formDialog.data.id"
              unelevated
              color="primary"
              type="submit"
              >Update address</q-btn
            >
            <q-btn
              v-else
              unelevated
              color="primary"
              :disable="
                formDialog.data.wallet == null ||
                formDialog.data.description == null ||
                !formDialog.data.custom_key ||
                !formDialog.data.custom_value
              "
              type="submit"
              >Create address</q-btn
            >
            <q-btn v-close-popup flat color="grey" class="q-ml-auto"
              >Cancel</q-btn
            >
          </div>
        </q-form>
      </q-card>
    </q-dialog>

    <!-- Detail dialog -->
    <q-dialog v-model="detailDialog.show" position="top">
      <q-card v-if="detailDialog.data" class="q-pa-lg lnbits__dialog-card">
        <p style="word-break: break-all">
          <strong>ID:</strong>
          <span v-text="detailDialog.data.id"></span><br />
          <strong>Description:</strong>
          <span v-text="detailDialog.data.description"></span><br />
          <strong>Custom Key:</strong>
          <span v-text="detailDialog.data.custom_key"></span><br />
          <strong>Custom Value:</strong>
          <span v-text="detailDialog.data.custom_value"></span><br />
          <strong>Webhook:</strong>
          <span v-text="detailDialog.data.webhook"></span><br />
          <span v-if="detailDialog.data.username">
            <strong>Well-known URL: </strong>
            <span v-text="wellKnownUrl(detailDialog.data)"></span>
            <q-icon
              name="content_copy"
              class="text-grey cursor-pointer q-ml-sm"
              @click="utils.copyText(wellKnownUrl(detailDialog.data))"
            ></q-icon>
            <br />
          </span>
        </p>
        <div class="row q-mt-lg q-gutter-sm">
          <q-btn
            v-if="detailDialog.data.username"
            outline
            color="grey"
            icon="link"
            @click="
              utils.copyText(
                wellKnownUrl(detailDialog.data),
                'Well-known URL copied to clipboard!'
              )
            "
            ><q-tooltip>Copy well-known URL</q-tooltip>
          </q-btn>
          <q-btn v-close-popup flat color="grey" class="q-ml-auto">Close</q-btn>
        </div>
      </q-card>
    </q-dialog>

    <!-- Send keysend dialog -->
    <q-dialog v-model="sendDialog.show">
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card">
        <q-form @submit="sendKeysend" class="q-gutter-md">
          <h6 class="text-subtitle1 q-my-none">Send Keysend Payment</h6>
          <q-select
            filled
            dense
            emit-value
            v-model="sendDialog.data.wallet"
            :options="g.user.walletOptions"
            label="From Wallet *"
          >
          </q-select>
          <q-input
            filled
            dense
            v-model.trim="sendDialog.data.destination"
            type="text"
            label="Destination pubkey (66-char hex) *"
          >
          </q-input>
          <q-input
            filled
            dense
            v-model.number="sendDialog.data.amount"
            type="number"
            label="Amount (sats) *"
            :rules="[val => val > 0 || 'Must be at least 1 sat']"
          >
          </q-input>
          <q-input
            filled
            dense
            v-model.trim="sendDialog.data.custom_key"
            type="text"
            label="Custom Key (optional)"
            hint="TLV record key, e.g. 696969"
          >
          </q-input>
          <q-input
            filled
            dense
            v-model.trim="sendDialog.data.custom_value"
            type="text"
            label="Custom Value (optional)"
            hint="TLV record value"
          >
          </q-input>
          <div class="row q-mt-lg">
            <q-btn
              unelevated
              color="primary"
              :disable="
                !sendDialog.data.wallet ||
                !sendDialog.data.destination ||
                !sendDialog.data.amount ||
                sendDialog.data.amount <= 0
              "
              type="submit"
              >Send</q-btn
            >
            <q-btn v-close-popup flat color="grey" class="q-ml-auto"
              >Cancel</q-btn
            >
          </div>
        </q-form>
      </q-card>
    </q-dialog>
  </div>
</template>
