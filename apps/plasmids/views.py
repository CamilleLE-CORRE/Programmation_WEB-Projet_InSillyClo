from django.contrib import messages
from django import forms
from django.forms import ValidationError
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views import View

from apps.correspondences import forms

from .forms import PlasmidSearchForm, PLASMID_TYPE_CHOICES, RESTRICTION_SITE_CHOICES,AddPlasmidsToCollectionForm, ImportPlasmidsForm
from .models import PlasmidCollection, Plasmid
from .service import import_plasmids_from_upload, get_or_create_target_collection




# class PlasmidList(TemplateView):
#     template_name = "plasmids/plasmid_list.html"

def plasmid_list(request):

    # A connected user can see both public and private plasmid collections
    if request.user.is_authenticated:
        plasmids = Plasmid.objects.all()

    # An unregistered user can only see public plasmid collections
    else:
        plasmids = Plasmid.objects.filter(collection__is_public=True)

    return render(request, 'plasmids/plasmid_list.html', {
        'plasmids': plasmids
    })

def plasmid_detail(request, identifier):
    
    # Get plasmid and verify it exists
    plasmid = get_object_or_404(Plasmid, identifier=identifier)
    
    return render(request, "plasmids/plasmid_detail.html", {
        "plasmid": plasmid
    })

class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PlasmidSearchForm(self.request.GET or None)
        context['form'] = form
        context['PLASMID_TYPE_CHOICES'] = PLASMID_TYPE_CHOICES
        context['RESTRICTION_SITE_CHOICES'] = RESTRICTION_SITE_CHOICES
        plasmids = Plasmid.objects.all()

        if form.is_valid():
            sequence_pattern = form.cleaned_data.get("sequence_pattern")
            name = form.cleaned_data.get("name")
            types = form.cleaned_data.get("types")
            sites = form.cleaned_data.get("sites")

            if sequence_pattern:
                plasmids = plasmids.filter(sequence__icontains=sequence_pattern)
            if name:
                plasmids = plasmids.filter(name__icontains=name)
            if types:
                plasmids = plasmids.filter(type__in=types)
            if sites:
                for site in sites:
                    plasmids = plasmids.filter(sites__icontains=site)

        context['plasmids'] = plasmids
        return context


class PlasmidSearchResultsView(TemplateView):
    template_name = "plasmids/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PlasmidSearchForm(self.request.GET or None)
        context['form'] = form

        plasmids = Plasmid.objects.all()

        if form.is_valid():
            # Champs texte
            sequence_pattern = form.cleaned_data.get("sequence_pattern")
            name = form.cleaned_data.get("name")
            if sequence_pattern:
                plasmids = plasmids.filter(sequence__icontains=sequence_pattern)
            if name:
                plasmids = plasmids.filter(name__icontains=name)

            # Types
            for t, _ in PLASMID_TYPE_CHOICES:
                choice = self.request.GET.get(f"type_{t}", "indifferent")
                if choice == "yes":
                    plasmids = plasmids.filter(type__icontains=t)
                elif choice == "no":
                    plasmids = plasmids.exclude(type__icontains=t)

            # Sites ER
            for s, _ in RESTRICTION_SITE_CHOICES:
                choice = self.request.GET.get(f"site_{s}", "indifferent")
                if choice == "yes":
                    plasmids = plasmids.filter(sites__icontains=s)
                elif choice == "no":
                    plasmids = plasmids.exclude(sites__icontains=s)

        context['plasmids'] = plasmids
        context['PLASMID_TYPE_CHOICES'] = PLASMID_TYPE_CHOICES
        context['RESTRICTION_SITE_CHOICES'] = RESTRICTION_SITE_CHOICES
        return context
    

# =================================================================================
# Plasmid Collections Views

class VisibleCollectionQuerysetMixin:
    """Collections visible to current user (public + owned)."""
    def get_queryset(self):
        qs = PlasmidCollection.objects.all()
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(Q(is_public=True) | Q(owner=user)).distinct()
        return qs.filter(is_public=True)

# List Views  
class CollectionListView(VisibleCollectionQuerysetMixin, ListView):
    model = PlasmidCollection
    template_name = "collections/collection_list.html"
    context_object_name = "collections"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["show_create"] = user.is_authenticated
        return ctx


class MyCollectionListView(LoginRequiredMixin, ListView):
    model = PlasmidCollection
    template_name = "collections/collection_list_mine.html"
    context_object_name = "collections"

    def get_queryset(self):
        return PlasmidCollection.objects.filter(owner=self.request.user).order_by("id")

    
# Detail View
class CollectionDetailView(VisibleCollectionQuerysetMixin, DetailView):
    model = PlasmidCollection
    template_name = "collections/collection_detail.html"
    context_object_name = "collection"

# Edit/Create/Delete Views
class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return self.request.user.is_authenticated and obj.owner_id == self.request.user.id


class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = PlasmidCollection
    template_name = "collections/collection_form.html"
    fields = ["name", "is_public", "team"]  

    def form_valid(self, form):
        form.instance.owner = self.request.user

        return super().form_valid(form)


class CollectionUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = PlasmidCollection
    template_name = "collections/collection_form.html"
    fields = ["name", "is_public", "team"]


class CollectionDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = PlasmidCollection
    template_name = "collections/collection_confirm_delete.html"
    success_url = reverse_lazy("plasmids:collection_list")


class CollectionAddPlasmidsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    GET: show collection detail + add form
    POST: move selected plasmids into this collection
    """
    model = PlasmidCollection
    template_name = "collections/collection_detail.html"
    context_object_name = "collection"

    def test_func(self):
        collection = self.get_object()
        return collection.owner_id == self.request.user.id

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        collection = self.object
        # Plasmides already in this collection
        ctx["plasmids"] = collection.plasmids.all().order_by("identifier")

        # Plasmides not in this collection (to add)
        selectable = Plasmid.objects.exclude(collection=collection).order_by("identifier")

        ctx["add_form"] = AddPlasmidsToCollectionForm(queryset=selectable)
        ctx["can_edit"] = True
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        collection = self.object

        selectable = Plasmid.objects.exclude(collection=collection).order_by("identifier")
        form = AddPlasmidsToCollectionForm(request.POST, queryset=selectable)

        if form.is_valid():
            selected = form.cleaned_data["plasmids"]
            count = selected.update(collection=collection)  # Bulk update
            messages.success(request, f"{count} plasmid(s) added to this collection.")
            return redirect(reverse("plasmids:collection_detail", args=[collection.pk]))

    
        ctx = self.get_context_data()
        ctx["add_form"] = form
        return self.render_to_response(ctx)
    


    

class PlasmidImportView(LoginRequiredMixin, View):
    template_name = "collections/plasmid_import.html"

    def get(self, request):
        form = ImportPlasmidsForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ImportPlasmidsForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        uploaded_file = form.cleaned_data["file"]
        target_collection = form.cleaned_data["target_collection"]
        new_collection_name = form.cleaned_data["new_collection_name"]

        collection = get_or_create_target_collection(
            owner=request.user,
            target_collection=target_collection,
            new_collection_name=new_collection_name
        )

        result = import_plasmids_from_upload(
            uploaded_file=uploaded_file,
            owner=request.user,
            collection=collection
        )

        # messages
        messages.success(
            request,
            f"Upload complete: {result.created} created, {result.skipped} skipped."
        )
        if result.errors:
            preview = ";".join(result.errors[:3])
            messages.warning(request, f"Some errors occurred during import: {preview}")

        # redirect
        if collection:
            return redirect(reverse("plasmids:collection_detail", args=[collection.pk]))
        return redirect(reverse("plasmids:plasmid_list"))